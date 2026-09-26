# When patch night, log harvesters, and a private ALB all fail in different ways

The Slack message wasn’t dramatic: “Filebeat not sending after the ASG refresh.” Same week we were mid-wave on AMI patching across several accounts, Jenkins was red on the frontend build agents again, and promo non-prod EKS was supposed to finish moving private ingress off CIDR rules onto security-group–based ALBs. No single pager owned the week—it was three unrelated failure modes that kept teaching the same lesson: **trust what the metric says**, and **don’t assume the loud error is the root cause**.

## What was moving

We run a familiar platform stack: ASGs backed by launch templates, SSM-driven patch runbooks (`Patching-ASG`, `NewRunbook`, `Ami-Patch`) with shared knobs—package excludes for java, elasticsearch, tomcat, nginx, agents, IMDSv2, dedupe by ASG, and we deliberately don’t overwrite the document default `TargetAmiName`. Logs go Filebeat → Logstash → indices; promo non-prod was cutting over ingress so Argo CD and the apps sit behind a private ALB whose access model was changing from “allow these CIDRs” to “allow this ALB security group.” Patch windows were already tight; critical prod Elasticsearch on pgdata was someone else’s execution window—we only prepped read-only SOP and backup AMI planning in the org.

I went into the week thinking patching automation would carry the load and EKS would be a config merge. Reality was messier.

## Patch night ate Jenkins first

Two consecutive mid-week patch nights, we lost **three to four hours each** before patching could finish—not because SSM lied, but because **Jenkins wouldn’t stay green**. Frontend builds on Node24 agents, deploy paths, the usual CI cluster. Patching and “get Jenkins working” weren’t parallel tracks; they were **coupled**. Until builds passed, we couldn’t treat patch night as done, and we couldn’t confidently promote AMIs.

On the AMI side, assisted runs did produce output AMIs for many ASGs, but a large batch **faltered**: wrong params, retries, timeouts, and **duplicate AMIs** for the same intent. When automation output looked suspect, **manual** no-reboot or standard `create-image` from a known-good instance was simpler and more trustworthy. Automation still earned its keep for param gathering and ASG dedupe—but **validate the AMI before LT promotion** and watch for dupes in the account became the informal gate.

Failures weren’t abstract:

- **Central Logstash ASG:** `InvalidAMIID.NotFound`. The LT/source AMI was deregistered while the instance still ran. Automation can’t `RunInstances` until you register a fresh AMI from the live node.
- **Graviton in one AZ:** `InsufficientInstanceCapacity`. Our retry policy was same subnet, same instance type—no family hop—so some ASGs just waited for capacity.
- **Promo ES master patch worker:** `NewRunbook` timed out on `verifySsmInstall` (20m). Cloud-init on **aarch64** tried a broken SSM agent install path (`Unsupported architecture aarch64`). The worker never registered in SSM; orphaned EC2 sat there until someone terminated it manually.

We also nailed down **source AMI logic**: when the running instance’s LT id/version has drifted from what the ASG thinks, use the **running instance AMI** as `SourceAmiId`, not the stale LT AMI.

Supporting ops around that: no-reboot backup AMIs for static IP lists, `yum history` plus uptime CSVs across long instance lists, ASG vs STATIC exports, service-tag CSVs for planning, and sweeps for **lingering automation workers** nobody admitted to leaving on.

Honest outcome: patch AMIs largely exist, with **quality and duplication debt** on the automated path. I’d rather bake manually once than promote twice.

## “Filebeat not sending” — harvesters before Logstash

After an ASG refresh, apps looked fine; the pipeline didn’t. My first instinct—check Logstash—was wrong, or at least **premature**.

Filebeat metrics told the story:

- `harvester.running: 0`
- `registrar.states: 0`

That means **no files are being read**. Output to Logstash is irrelevant until harvesters run. Root cause was **wrong Filebeat config**: paths and inputs didn’t match where the app actually writes (generic template vs trees under `/paytm/logs/...`). We fixed it manually after debugging; metrics flipped once paths aligned.

We still had to rule out fleet issues:

- **750 dirs / 640 files** permission model if the filebeat user isn’t the app user.
- Ansible **security group** gaps—filebeat role missing on some boxes, Promtail still on others—a separate fleet fix from the one-off config correction.

Logstash did throw noise if you went looking: `InvalidFrameProtocolException` for beats protocol **10** and **13** on 5044, bytes matching HTTP CRLF. Plain `beats { port => 5044 }`, Filebeat `output.logstash` without SSL. That pattern screams **HTTP health checks on the Beats port** or random TCP that isn’t Beats—not “Logstash is down.” Fix on that side is **TCP health checks on the LB**, not HTTP on 5044.

Diagnostic order I’ll keep: **harvesters → paths/perms → then** protocol errors on Logstash (often LB HTTP on 5044).

On EKS, Alloy work in promo namespace was a different slice—split container logs so lines starting with `[TOMCAT]` go to `*-tomcat-logs`, everything else to `*-app-logs`. That’s routing hygiene, not the EC2 Filebeat miss.

## EKS ingress: SG ALB without the traffic path

We completed the move from **CIDR-based private ALB** to **security-group inbound** (`alb-private-sg` values), dropped legacy CIDR ingress objects and `alb-private.yaml` from Argo valueFiles, and brought **Argo CD ingress** through the same cutover. It shipped live with **tcp/8080** from the ALB SG onto cluster and node SGs. No major outage was reported.

The gotcha we already knew from older shared ALBs, and it bit again: custom ALB SG on ingress **without** the LBC-managed “traffic” SG → **all targets unhealthy / timeout** until you allow **tcp/8080 from the ALB SG onto cluster and node security groups**. Same pattern, new values file.

Deploy model shifted too: stopped Argo Rollouts canary for promo apps; **RollingUpdate** Deployment with `maxUnavailable: 0` where we configured it.

Housekeeping surfaced a listener mismatch: **pgvalidate** host `/prometheus` returned fixed **503** “Backend action does not exist” while promo-admin forwarded `/prometheus` to targets—missing or wrong listener rule for the pgvalidate metrics path. Not cutover-blocking for the SG migration, but embarrassing next to a green ingress story.

Storm CI got aligned with other promo apps—Jenkins docker build plus topology deploy, one image tag deployable to multiple topologies with `sleep infinity` entrypoint and jar submit path separate. Infra pod timezone audit (UTC vs IST) and a readonly pass on why a gateway deployment scaled one pod at a time (HPA/PDB/scheduling) filled the gaps between merges.

## Side threads that didn’t own the week

OpenSearch dedicated masters sitting at **~97–98% OS RAM** on ~16 GiB nodes with **~26–70% JVM heap** looked alarming until you remember fixed ~10 GiB heap—the OS “used” number isn’t heap pressure; data nodes looked healthier on OS % because of larger RAM and mapped buffers.

Prometheus: new EKS scrape job for promo non-prod, same Jenkins encrypt-secret pattern as other EKS jobs. Governance: script to copy EC2 instance governance tags to attached EBS volumes, dry-run then `--apply`, tested on one instance before fleet.

UMP/dashboard firefighting: preprod Tomcat catalina errors; **Vault token lookup-self 403** on one box vs healthy peer (compare properties, refresh path from working host). Preprod nginx `Permission denied` on `ump-login/index.html`—filesystem perms on the static root, not upstream. Argo CD dev local accounts on ATS prod/stage. Mobile API intermittent curl with Android headers—Host vs CDN/Akamai hostname variants. Pinpoint ansible tag-only on Tomcat. All real tickets, none the spine of the week.

## What I’d do again—and what I’d change

**Patch AMI triage** is a checklist now: does the AMI exist? dupes in the account? capacity in subnet/AZ? SSM on the worker? If automation output is suspect, **manual bake** beats promoting twice. And **Jenkins green** before declaring patch night done—it’s a dependency, not sidebar work.

**Logs missing** starts at Filebeat harvesters, not Logstash tail -f.

**EKS private ALB SG migration** isn’t done when Argo syncs; it’s done when **ALB SG → pod:8080** is on cluster **and** node SGs.

The week didn’t give one flagship incident worth its own novel; it gave a stack of medium items that shared mechanics—wrong assumption about which layer was broken, automation output that needed human gates, and infra changes that look complete in Git before traffic actually flows. If I were writing this for the team, I’d probably title the internal handover “platform whack-a-mole” and keep one table of symptoms: harvester zero vs AMI not found vs target timeout. For a blog, the through-line is enough: **read the metric that can’t lie, validate artifacts before promotion, and treat CI health as part of the change window**—because that week, Jenkins owned as many hours as SSM did.