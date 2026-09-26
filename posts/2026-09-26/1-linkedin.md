# LinkedIn draft (from your template)

**Option A — single post (recommended length)**

---

Another week in platform ops: less one big incident, more a stack of things that only show up when you change the fleet.

**Patching at scale** — We ran bulk AMI patching across multiple accounts with shared runbooks (excludes, dedupe by ASG, careful source-AMI logic). We got AMIs out the door, but automation-assisted runs also surfaced wrong params, timeouts, and duplicate images for the same intent. The honest lesson: automation is great for gathering params and deduping — **validate before you promote launch templates**. When output looked wrong, a known-good manual bake was faster and more trustworthy. When we patched in place on ASG members, we learned the hard way that a long patch or bad reboot can fail health checks and trigger **replacement instances that don’t carry pet config** (agents, log paths, local fixes). The pattern that stuck: **Standby → patch → reboot → verify (including kernel actually booted, not just installed) → back InService**. Bonus trap: `yum` installing a new kernel ≠ running it until grub default is right.

**Logs after refresh** — “Filebeat not sending” wasn’t Logstash down. Metrics said it all: **zero harvesters** until paths matched where apps actually write. Fix the shipper first; protocol noise on the collector is a distant second.

**Non-prod EKS** — Cut over private ingress from CIDR-based ALB rules to **security-group–driven** access, simplified GitOps values, and rolled deployments instead of canary for managed apps. Shipped without a major outage — after remembering the classic gotcha: custom ALB SG means you still have to allow **ALB → workload** on the right ports on cluster and node SGs.

**Reality check** — Two patch nights ran long because **CI agents and builds** failed in parallel. Infra windows aren’t independent of Jenkins health.

Grateful for tickets, runbooks, and teammates who debug grub at midnight. Platform work is often many medium wins — and one table of symptoms beats three heroic war stories.

#DevOps #SRE #Kubernetes #AWS #Observability #PlatformEngineering

---

**Option B — shorter (scroll-friendly)**

---

Week in platform: patching wave, log pipeline gaps after ASG refresh, and non-prod EKS ingress cutover — no single flagship incident, lots of medium complexity.

**Impact:** Patch AMIs largely created (with automation quality debt we’re gating before LT promotion). Non-prod **private ALB on security groups** is live with rolling deploys. Filebeat shipping restored after **config/path fixes**, not a Logstash outage.

**Hard parts:** Automation dupes and timeouts → validate AMIs, prefer manual bake when suspect. In-place ASG patching → **Standby** before reboot, verify **kernel is actually running**, expect replacements to miss pet config. Missing logs → **harvester metrics first**, then collector.

**Coupling:** Jenkins agent/build issues added **3–4 hours** on two patch nights — CI health is part of the change window, not a sidebar.

That’s the job some weeks: whack-a-mole across patch workers, log shippers, and ALB rules — with clearer playbooks on the other side.

#SRE #AWS #EKS #Logging

---

**What I deliberately left out** (per your sanitize rules): account IDs, hostnames, internal job/token patterns, specific ASG/SSM document names, Elasticsearch maintenance execution, Storm topology detail (prior week), and ticket IDs.

If you want a different tone (more “lesson learned” vs “week roundup”), or a **carousel outline** (one slide per layer: patch / logs / EKS), say which option to extend.