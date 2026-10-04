# LinkedIn draft (from your template)

**Option A — short**

Pods stuck Pending on our EKS cluster while nodes looked “empty” in `kubectl top`. Karpenter kept saying every instance type exceeded NodePool limits.

The twist: Karpenter counts **full instance capacity** toward pool limits—not live usage. Our CPU cap had room, but the **memory cap** was too tight for the Graviton shapes we were launching, so no new nodes could join. A hardcoded instance-type list made it worse—when one size didn’t fit the budget, nothing else could.

We fixed it in GitOps: raised the memory limit to match the CPU budget and let Karpenter pick among arm64 on-demand types in our allowed families. Rollouts and scheduling unblocked.

Lesson: Pending + “exceed limits” + healthy-looking `top` → check **pool limits vs counted capacity** before you chase utilization.

---

**Option B — slightly more narrative**

Ever debug scheduling when the cluster *looks* fine?

We had app pods Pending during a busy sync window. Nodes showed low CPU in `top`, but the scheduler had nowhere to place new workloads—and Karpenter wouldn’t provision.

Root cause was two-fold: NodePool **memory** limit was sized like CPU (80 cores vs 80Gi), but each new node bills its **full** memory against that cap. We were ~1Gi shy of fitting another node. Plus we’d pinned the pool to only two instance types, so Karpenter couldn’t trade shape for a better fit.

Outcome: blocked rollouts until we aligned limits with how Karpenter actually accounts for capacity, and removed the instance-type straitjacket.

If you run Karpenter: limits are the sum of **instance sizes in the pool**, not what `top` shows. That symptom triad—Pending, “exceed limits,” idle-looking nodes—is worth memorizing.

---

**Option C — one-liner hook + bullets**

**Hook:** The cluster wasn’t out of CPU—it was out of *accounting*.

- **Challenge:** Pending pods; Karpenter: “all instance types exceed limits”; `kubectl top` looked fine  
- **Why:** Pool memory cap too low for the CPU cap + hardcoded instance types  
- **Fix:** GitOps—memory limit ~2× CPU-oriented cap; broader arm64 instance selection  
- **Impact:** Scheduling and rollouts unblocked; fewer false “we have capacity” reads  

**Takeaway:** On Karpenter, NodePool limits = billed instance capacity, not utilization.

---

### Sanitization check
- No account/cluster names, internal repo paths, or mesh/vendor specifics beyond generic “sync activity”
- Technical terms kept where they signal credibility (Karpenter, NodePool, GitOps, EKS)
- Impact framed as scheduling/rollouts, not internal service names

Want this tightened for a **character limit**, tagged for **#Kubernetes / #EKS / #PlatformEngineering**, or toned more **leadership vs practitioner**? Say which option and audience—I’ll reshape it (still Ask mode; no edits to your repo).