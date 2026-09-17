**Phase 1 — LinkedIn draft**

Here’s a concise, professional post based on your template and sanitized evidence:

---

**Option A (recommended — story + lessons)**

There’s no official Apache Storm Helm chart. No credible “migrate Storm to Kubernetes” guide. And in our org, nobody had run Storm on EKS before.

So when we were asked to move a streaming workload onto the same Kubernetes platform as the rest of our apps — instead of keeping a separate EC2 fleet — we knew we were building the path, not following one.

**The challenge:** Stateful control plane (ZooKeeper, Nimbus) on ephemeral, auto-scaled nodes. Private container images that don’t match upstream docs. GitOps with StatefulSets. A shared load balancer pattern that had to work like every other app on the cluster.

**What we shipped:** A custom Helm chart, deployed via Argo CD on ARM nodes — ZK and Nimbus on persistent volumes, supervisors and Storm UI as deployments, log viewing wired into the UI, and ingress on our standard private ALB pattern.

It wasn’t smooth. Storage classes didn’t match what the chart expected — PVCs sat Pending and everything downstream waited on Nimbus. Image entrypoints weren’t `nimbus` and `ui`; they were `storm nimbus` and `storm ui`. Argo kept flagging StatefulSet volume drift. The load balancer controller wanted `target-type: ip` and numeric backend ports, not named ports with instance targets.

We fixed each layer, documented the failure modes, and ended the week with a healthy GitOps deployment.

**The result:** The first Storm cluster on EKS in our organization — proof that we can run streaming control plane + workers on the same platform as everything else, without inventing a third deployment model.

**What I’d tell the next team:** Verify StorageClass on the target cluster before you ship StatefulSets. Test private image entrypoints; don’t trust upstream Helm examples. Plan for Argo + `volumeClaimTemplates` drift. And if you’re first in the org, write down the fears upfront — storage, ARM, HA, logs — and validate them on cluster, not in a doc.

Sometimes there is no paved road. You still have to get there.

#Kubernetes #ApacheStorm #PlatformEngineering #GitOps #EKS

---

**Option B (shorter — impact-first)**

We just stood up the **first Apache Storm cluster on EKS** in our org — with no official Helm chart and no internal playbook to copy.

Custom Helm + Argo CD on auto-scaled ARM nodes. Stateful ZK/Nimbus on PVCs. Supervisors and Storm UI on the same GitOps patterns as the rest of our platform.

The hard parts weren’t Storm itself — they were the gaps: missing StorageClass → PVCs Pending → init containers waiting forever. Private images needing `storm nimbus`, not `nimbus`. Argo OutOfSync on StatefulSet volumes. ALB ingress needing IP targets and numeric ports.

All resolved. Cluster healthy. Failure modes documented for prod and the next environment.

Greenfield streaming on Kubernetes is DIY. Budget time for chart work, image archaeology, and a honest pre-flight checklist.

#PlatformEngineering #Kubernetes #ApacheStorm #EKS #GitOps

---

**Sanitization notes (what I left out):**
- Account/team names, “promo,” specific dates, ECR/ALB config file names
- Full component tables and phased rollout detail (kept in narrative form)
- Open prod questions (ZK HA, topology submit, log durability) — fine as a follow-up comment if you want

**Tweaks you might want:**
- Swap “our org” → “my team” if you want it more personal
- Add one concrete outcome line if you have a safe metric (e.g. “retired separate EC2 fleet for non-prod”)
- Trim hashtags to 3–4 for a cleaner look

Want a **more technical** version (named components/table) or a **more leadership-focused** one (cost/ops surface, platform consolidation)? I can draft that in Phase 2.