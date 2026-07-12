Here are a few LinkedIn-ready options based on your template and evidence.

---

## Option 1 (recommended — concise)

**Evicted pods don’t always disappear on their own.**

While investigating a cluster health issue, we found dozens of pods stuck in `Evicted` state on a single node after **DiskPressure** — while new replicas had already spun up and kept the service healthy.

The surprise: **evicted pods aren’t automatically terminated.** They sit until the **kubelet garbage collector** runs or someone cleans them up manually.

**Outcome:** No user impact, but a good reminder that “healthy workload” ≠ “clean cluster.” Left alone, stale evicted pods can clutter the node and tie up resources like IPs over time.

**Takeaway:** On managed Kubernetes (EKS), eviction cleanup behavior isn’t always obvious — worth knowing your GC thresholds and having a cleanup path before it becomes a real problem.

---

## Option 2 (slightly more technical)

**Not every Kubernetes failure mode shows up in your dashboards.**

We traced ~100 evicted pods to one node under disk pressure. Replacements were already running, so there was no production impact — but the old pods were still there, not terminating.

Root cause wasn’t a bug in our app: **evicted pods wait for garbage collection or manual deletion.** They don’t exit the cluster on their own.

**What we learned:**
- Eviction ≠ termination
- New replicas can mask the mess
- On EKS, GC tuning isn’t as visible as on self-managed clusters

Small issue today, but the kind that compounds if you ignore it.

---

## Option 3 (short / punchy)

**Kubernetes taught me something subtle this week:**

Pods can be **Evicted** and still **not Terminating**.

Disk pressure hit one node. New pods came up fine — no outage. But dozens of evicted pods lingered, waiting on the garbage collector or manual cleanup.

No impact *yet*. But it’s a good lesson: **always look at node-level state, not just “are my replicas healthy?”**

---

## Optional closing line (pick one)

- *What’s your approach for cleaning up evicted pods — automation, alerts, or periodic sweeps?*
- *Has anyone found clear GC threshold docs for EKS? Would love pointers.*
- *Sometimes the best incidents are the ones that never hit users — but still teach you something.*

---

## Notes for your “remember” item

If you want to mention the GC threshold research without sounding blocked:

> *On self-managed clusters, kubelet flags like `--eviction-hard` and `--image-gc-high-threshold` are well documented. On EKS, those knobs are managed for you — so the practical fix is often monitoring + cleanup automation rather than tuning a single threshold.*

That keeps the post outcome-focused and avoids implying you’re stuck.

Want me to tailor one version to a specific tone (more junior-friendly, more SRE-focused, or shorter for a quick post)?