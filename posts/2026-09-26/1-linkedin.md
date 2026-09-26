# LinkedIn draft (week roundup)

**Option A — single post (recommended)**

---

Another week in platform ops: fewer fireworks, more steady fixes—and a few lessons I’ll carry forward.

**Patching at scale**  
We pushed AMI updates across multiple AWS accounts using SSM runbooks—shared excludes, dedupe by ASG, careful source-AMI logic when launch templates drift. We got AMIs out, but a big batch of assisted runs tripped on params, timeouts, and duplicate images. When output looked wrong, **baking from a known-good instance and validating before launch-template promotion** beat trusting automation blindly. Patch nights also ran long because **Jenkins wasn’t green**—CI recovery and patching turned into one coupled stream, not two parallel tracks.

**Logs that “stopped working”**  
After an instance refresh, “Filebeat isn’t sending” often isn’t Logstash—it’s **harvesters at zero** because paths don’t match where the app actually writes. Fix the inputs and permissions first; only then chase downstream protocol noise (e.g. HTTP probes hitting a Beats port).

**Promo non-prod EKS**  
We finished moving private ingress from CIDR rules to **security-group–based ALB access**, simplified deploys (rolling updates instead of canary for these apps), and shipped **without a major outage**. The gotcha that bit us before: custom ALB security groups need **explicit pod/node paths** (e.g. TCP to app port from the ALB SG)—same pattern as the old shared load balancer.

**Impact:** Ingress cutover live and stable; log shipping restored where configs were wrong; patch AMIs largely created with clearer gates on quality and dupes. Two patch nights cost an extra **3–4 hours each** on CI firefighting.

Platform work is often a stack of medium items, not one hero incident. This week reinforced: **validate artifacts before promotion, treat CI as a patch-night dependency, and debug logs from the shipper inward.**

#DevOps #PlatformEngineering #AWS #Kubernetes #Observability

---

**Option B — shorter (if you prefer minimal)**

---

Week in review: AMI patching across accounts, EKS ingress cutover (CIDR → SG-based private ALB), and “missing logs” that were really **wrong Filebeat paths** after refresh—not a Logstash outage.

Wins: promo non-prod ingress **live without major outage**; shipping fixed after config correction; patch images produced at scale.

Honest lesson: automation helped with params and dedupe, but **duplicate/suspect AMIs** meant manual bake + validate-before-LT was faster to trust. **Jenkins failures added 3–4 hours to two patch nights**—CI health is part of the change window, not a sidebar.

Debug order I’ll reuse: harvesters → paths/perms → then downstream. ALB SG migrations: don’t forget **ALB SG → workload port** on cluster and node security groups.

#PlatformEngineering #AWS #EKS

---

**Sanitization notes (what I left out)**  
- Account names, specific ASG/hostnames, internal tools (Argo job names, document IDs)  
- Elasticsearch pgdata prep (handoff-only), Vault/nginx ticket detail, Storm prior-week story  
- Redacted token/Prometheus specifics  

**Optional hook** (from your “remember”): if you want a slightly more narrative angle, open with: *“Not every week has one flagship incident—sometimes it’s three layers of whack-a-mole: patch workers, log shippers, and one missing ALB rule.”* Then use Option A’s three bullets.

I can tune tone (more technical vs. more leadership), length, or first-person vs. team voice if you say which audience you’re targeting.