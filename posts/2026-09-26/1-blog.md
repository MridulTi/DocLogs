# Patch night wasn’t one incident — it was three failure modes in a row

Tuesday’s plan looked boring on paper: run the SSM patch runbooks across a bunch of Auto Scaling Groups, bake AMIs, promote launch templates, go home. By midnight I was still on a call with Jenkins console output in one terminal and `aws autoscaling describe-auto-scaling-groups` in the other. Nobody had paged us for a single catastrophic outage. What we had was worse in a different way — a pile of medium failures that kept teaching the same lesson: **the platform replaces your box faster than you can trust what’s on disk**.

---

We’re on several AWS accounts in `ap-south-1`, with a mix of ASG-backed app tiers, central Logstash, non-prod EKS behind private ALBs, and Jenkins still in the middle of deploy paths. The week of 19–26 Sep was a patching wave plus finishing non-prod EKS ingress cutover, logging gaps on refreshed EC2, and the usual Jenkins/Argo/dashboard tickets. Storm-on-EKS had already been written up the week before; this one was the “everything else” shift.

I’ll focus on three threads that actually changed how I work: **patch automation that lied**, **Filebeat that looked like Logstash**, and **an ALB that went healthy only after we remembered how traffic really flows**.

---

## When the runbook finishes but the AMI doesn’t

We drove bulk patching through SSM documents — `Patching-ASG`, `NewRunbook`, `Ami-Patch` — with shared params: package excludes (java, elasticsearch, tomcat, nginx, agents, and friends), IMDSv2 metadata, no overwriting the document default `TargetAmiName`, dedupe by ASG. On paper that’s the right shape. In practice, a large batch of assisted runs **faltered**: wrong params, retries, timeouts, and **duplicate AMIs** for the same intent. AMIs *existed*, but I stopped trusting “green” in the SSM console as “safe to put in the launch template.”

My triage order became mechanical: does the AMI exist? Are there dupes for the same ASG intent? If we’re launching replacements, is it `InsufficientInstanceCapacity` on Graviton in one AZ — where our retry policy was **same subnet, same instance type**, no family hop? Is the worker even in SSM? When automation output looked suspect, **manual no-reboot / standard create-image from a known-good instance** was slower but honest. Automation was still worth it for param gathering and dedupe logic; **validate before LT promotion** was the gate we’d been skipping in spirit.

Two failures stuck in my notes. On a central Logstash ASG we hit `InvalidAMIID.NotFound`: the launch template (or source AMI) was deregistered while the instance kept running. Automation can’t `RunInstances` until you register a fresh AMI from the live node — the running box is the source of truth, and when the running instance’s LT id/version had drifted from what the ASG thought it was using, **`SourceAmiId` had to come from the running instance AMI**, not a stale LT pointer.

The other was uglier: `NewRunbook` timed out on an Elasticsearch master patch worker at `verifySsmInstall` after 20 minutes. Cloud-init on **aarch64** tried to install SSM via a path that blew up with `Unsupported architecture aarch64`. The worker never registered; we had an orphaned EC2 until someone terminated it manually. That’s a recurring risk I’m now paranoid about: **arm64 first-boot SSM install paths that don’t match the AMI family.**

With patch AMIs unreliable, we fell back to **in-place patching on ASG members** — `yum update`, reboot for kernel. First time through, I learned this is not “SSH and yum” in a vacuum.

I patched what I thought was a “safe” instance — termination protection in my head, “this one shouldn’t be replaced.” The ASG **still replaced** it. Long patch window or a bad reboot fails the health check; the group launches from the launch template. Those replacements are **not** clones of the old disk. Fresh boot, often **missing** agents, log paths, local tuning, manual fixes from three incidents ago. We turned one patching task into config drift repair on top of Jenkins already being on fire.

The pattern we landed on: **ASG Standby**. One member at a time — move to Standby (out of rotation, still running), patch, reboot, validate, back to InService. It doesn’t make the ASG magic, but it cuts the odds that traffic and health checks drive a replace cycle on the box you’re mid-flight on. You still coordinate desired capacity and which AZ you’re touching.

Then the kernel trap. `yum` installed a new kernel; we rebooted; `uname -r` still showed the **old** kernel. On RHEL-family AMIs that often means the boot loader default never moved — `grub2-set-default`, read `/etc/default/grub`, `grub2-mkconfig`, fix the right **BOOT** entry and cmdline, reboot **again**, verify. “Patched and rebooted” is not “running the new kernel.” First time through that was trial and error; I didn’t capture exact timings, but it burned a chunk of the window.

Meanwhile Jenkins wasn’t a sidebar. On two consecutive patch nights (~mid-week), frontend build agents, deploy paths, and related CI failures ate **3–4 hours each night** before patching could finish. Patch work, ASG churn, config repair, and CI recovery were **coupled**. I’d call patch night done only after agents were healthy — lesson learned the expensive way.

---

## `harvester.running: 0` and why I stopped blaming Logstash first

Separate thread, same week: “Filebeat not sending” after an ASG instance refresh. My instinct — and I’ve seen teams do this — is to stare at Logstash or OpenSearch. The metrics told a different story: **`harvester.running: 0`**, **`registrar.states: 0`**. Filebeat wasn’t reading files. Output to Logstash is irrelevant until harvesters run.

We walked paths and permissions. Generic template inputs didn’t match where the app actually wrote logs — path mismatch. Directories at **750** and files at **640** bite when the filebeat user isn’t the app user. Fix was **manual config correction after debugging**; shipping came back when paths aligned. Not primarily a Logstash outage.

Logstash did throw noise if you went looking: `InvalidFrameProtocolException` for Beats protocol **10** and **13** on port 5044. Bytes looked like HTTP CRLF. Plain `beats { port => 5044 }` on Logstash; Filebeat `output.logstash` without SSL. Likely something doing **HTTP health checks on the Beats port** or random TCP to 5044 — fix on the LB side is **TCP health check**, not HTTP on 5044. I keep that diagnostic order now: **harvesters → paths/perms → then** protocol errors on the collector.

Fleet-wise, Ansible had security-group gaps — filebeat role missing on some boxes, Promtail still on others. That’s a separate fix from the one-off path correction, but it explains why refresh keeps biting the same org.

On EKS we were also splitting Alloy streams for application-namespace container logs — lines starting with `[TOMCAT]` to `*-tomcat-logs`, everything else to `*-app-logs`. Different layer, same theme: **the pipeline is only as good as the contract at the edge**.

---

## Private ALB by security group, and the 8080 rule we almost forgot

Non-prod EKS ingress finished a move from **CIDR-based private ALB** to **security-group inbound** (`alb-private-sg` values). We removed legacy CIDR ingress objects and dropped `alb-private.yaml` from Argo valueFiles; Argo CD’s own ingress rode the same cutover. Shipped live with **tcp/8080** from the ALB security group onto cluster and node security groups. **No major outage** was reported — which still doesn’t mean it was free.

The gotcha we’d seen on older shared ALBs came back: custom ALB SG on the ingress **without** the LBC-managed “traffic” SG means targets sit **unhealthy / timeout** until you explicitly allow **tcp/8080 from the ALB SG onto cluster and node SGs**. Same pattern as before; easy to forget when the manifest “looks” right in Git.

Deploy model shifted too: stopped Argo Rollouts canary for GitOps-managed apps in favor of **RollingUpdate Deployment** with `maxUnavailable: 0` where we configured it — less ceremony, more predictable rollouts for that environment.

Smaller ALB puzzle on the same listener: one app’s host + `/prometheus` returned a fixed **503** “Backend action does not exist” while another app on the **same** ALB forwarded `/prometheus` fine. Missing or wrong listener rule for the first app’s metrics path — not a pod problem, a rule problem.

Storm CI got Jenkins docker build + topology deploy aligned with other container workloads; one image tag deployable to multiple topologies with entrypoint `sleep infinity` and jar submit on a separate path. Housekeeping that week included infra pod timezone audit (UTC vs IST) and readonly digging on why a gateway deployment scaled one pod at a time — HPA/PDB/scheduling, not glamorous but real.

---

## What I’d do again (and what I’m watching)

This wasn’t a single root-cause postmortem; it was **platform whack-a-mole** with a few sharp takeaways tied to what we actually touched.

**Patching:** Gate automation output — dupes, timeouts, arm64 SSM workers — before LT promotion. In-place on ASGs: **Standby → patch → reboot → verify `uname -r` and grub default → InService**. Expect LT replacements to **lack pet config**; don’t rely on disk state — Ansible, agents, or pull-based config has to be the default. Treat **Jenkins health as a dependency** on patch night, not a parallel ticket you’ll “get to.”

**Logs:** If harvesters are zero, fix Filebeat before Logstash. HTTP on 5044 is a distraction with a real fix elsewhere.

**EKS ingress:** SG-based private ALB is fine if you remember the **ALB SG → node/cluster SG on 8080** contract every time.

OpenSearch dedicated masters at ~97–98% OS RAM on ~16 GiB nodes with ~26–70% JVM heap looked alarming until we reconciled fixed ~10 GiB heap with OS “used” not equaling heap pressure — data nodes looked healthier on OS % because of larger RAM and mapped buffers. Critical Elasticsearch data-tier patch/reboot was **prep and read-only SOP** on our shift, not execution — I’m glad that stayed someone else’s careful window.

Governance housekeeping: script to copy EC2 instance governance tags to attached EBS volumes (dry-run vs `--apply`), tested on one instance before fleet. Prometheus got a new EKS scrape job on non-prod with the same Jenkins encrypt-secret pattern as other EKS jobs.

If I’d publish one table from the week for my own notebook, it would be symptoms vs layer: duplicate or missing patch AMI → **automation/LT**; fresh ASG instance missing agents/logs → **replace churn + config drift**; logs “not sending” with zero harvesters → **Filebeat paths/perms**; ALB targets timeout → **SG rules on 8080**, not the app. Nothing here is a new framework — it’s the kind of week where three boring layers stack up and the job is to **not mistake the symptom’s loudest service for the broken contract**.

Next patch wave, I’m validating AMIs before promotion, running Standby on in-place work, and checking Jenkins agents before I call the night done. The rest can stay in tickets — but those three habits would have saved us half the hours we didn’t get back.