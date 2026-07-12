# Ninety-seven evicted pods that refused to die

The alert wasn't about user-facing errors. It was a node inventory check that came back wrong: **97 pods** stuck in `Evicted`, all pinned to the same worker. Disk pressure had already done its job — the kubelet had thrown them out to reclaim space — and the controllers had done theirs too. Deployments and ReplicaSets had spun up replacements elsewhere until everything looked healthy again. From the outside, the cluster was fine.

From inside `kubectl get pods --all-namespaces`, it wasn't fine. Ninety-seven rows with `STATUS=Evicted`, `RESTARTS=-`, sitting there like debris after a storm. They weren't terminating. They weren't going away. They were just… present.

## What we were running

We're on **EKS**. Workloads are mostly stateless services behind Deployments; when a pod dies, the controller replaces it. That model usually means you don't stare at individual pod lifecycles — you watch readiness and error rates, and the platform handles the churn.

This incident didn't break that model. Nothing was down. The evictions happened on one node under **DiskPressure**, new replicas landed on other nodes, and traffic kept flowing. The weird part was what happened *after* the recovery: the old pods didn't disappear. They accumulated.

That's worth taking seriously even when there's no immediate outage. Evicted pods still exist as API objects. They still show up in listings, still tie up mental overhead for anyone debugging the cluster, and — the part that made us uneasy — they may still hold **IP addresses** from when they were running. I don't have a clean number from that day for how many IPs were effectively reserved, but the concern was straightforward: if this pattern repeats across nodes or over weeks, you can end up with address-space and housekeeping problems that are annoying at first and painful later.

## Starting with the obvious wrong answers

My first instinct was controller lag. Maybe the Deployment hadn't reconciled yet, or something was wedged in the scheduler. But the evicted pods weren't supposed to be *reconciled* — they were already gone from the node's point of view. Their replacements were running. Checking a few of the evicted objects confirmed it: same owner references, new healthy pods elsewhere, old ones frozen in a terminal-ish state that wasn't actually terminal in the API.

Next I wondered if something was blocking finalizers. That's a common reason objects hang around. These didn't have the telltale stuck-finalizer smell; they looked like normal failed pods that something simply wasn't cleaning up.

I also briefly chased **DiskPressure** itself — could the node still be under pressure and preventing cleanup? Worth checking, but it didn't explain the behavior. Eviction had already happened. The node had shed load. The pods' phase was `Failed` with reason `Evicted`. The problem wasn't "why were they evicted"; we more or less knew that. The problem was "why are they still here."

That narrowing mattered. It's easy to burn an hour re-tuning eviction thresholds when the cluster has already evicted exactly what you'd expect it to evict.

## The actual mechanism (and why it felt broken)

The answer, once we stopped looking for a bug in *our* manifests, was Kubernetes behavior that doesn't match intuition if you've only ever watched pods get deleted when you `kubectl delete` them.

**Evicted pods are not automatically terminated and removed.** Eviction is a kubelet action: the node ejects the workload to protect itself. The pod object transitions to `Failed` / `Evicted`. But deletion is a separate step. Unless something deletes the pod, it stays in the API until:

1. Something (or someone) explicitly deletes it, or  
2. The **pod garbage collector** decides there are enough terminated pods to warrant a sweep.

That second path is where we hit the wall on EKS.

On a self-managed cluster, you can reason about kubelet flags. There's a knob people reach for in this situation: **`terminated-pod-gc-threshold`**. The kubelet won't garbage-collect terminated pods until the count of terminated pods on that node exceeds the threshold. The default in upstream Kubernetes is very high — on the order of **12,500** — which means in practice, for most clusters, **GC almost never triggers on count alone**. Evicted pods can sit indefinitely.

We wanted to confirm what EKS was actually running. What threshold did our nodes use? Was GC even in play? I couldn't find a documented, accessible value for the garbage collector threshold on our EKS setup. Managed control plane, managed node groups — kubelet configuration isn't something you SSH in and inspect the way you might on k3s in a lab. We checked what we could from the outside (node descriptions, kubelet config surfaces available to us) and didn't get a crisp answer. That's the honest blocker from this incident: **on EKS, the "wait until GC catches up" strategy is a black box you don't fully control**, and 97 pods is nowhere near a threshold that would matter even if it were the upstream default.

So the behavior we saw wasn't a one-off glitch. It was the system working as designed, with a cleanup path that's either manual or extremely lazy.

## What we did about it

Since there was no production impact, we had room to fix housekeeping without a fire drill. The fix was conceptually simple even if the root cause was annoying:

**Don't wait for garbage collection. Delete evicted pods deliberately.**

For a one-time cleanup on a single noisy node, that's manual deletion — `kubectl delete pod` on the evicted objects, or a narrow script/filter that targets `status.reason=Evicted`. For something you don't want to think about again, a small controller or cron-style job that periodically removes evicted pods is the usual pattern. (I don't have the exact command we ran preserved in my notes; it was the boring kind: list evicted pods on the affected node, delete them, verify count goes to zero.)

Why that works: eviction already did the important work — freed the node, stopped containers. Deleting the API object releases the last bits of cluster state associated with the pod, including the lingering identity/IP bookkeeping that made us nervous about letting this slide for weeks.

What we did **not** do, because it wasn't the problem in front of us: rewrite eviction thresholds to prevent DiskPressure. Disk pressure on one node is its own follow-up (image garbage collection, log rotation, disk size, noisy neighbors). But even a perfectly tuned node will leave evicted pods behind if nobody deletes them. Cleanup and prevention are related themes; they're not the same fix.

## What I'd do differently next time

Two takeaways, both specific to this incident rather than generic SRE poster slogans.

**First:** Treat `Evicted` as a state that requires an operator response, not a self-healing terminal state. If your mental model is "kubelet evicts → pod goes away," you'll miss exactly this class of clutter. A dashboard or alert on *count of evicted pods* — especially per node — is cheap and would have caught the 97-pod pile-up earlier, even while users were unaffected.

**Second:** On managed Kubernetes, **ask "who deletes this object?"** before assuming the platform will. EKS absolves you of a lot, but not of orphaned API objects after node-level eviction. I still want a definitive answer on garbage collector threshold for our node groups — that's the open thread I marked "remember" when we closed this out. Until we have it, I wouldn't bet production hygiene on GC.

We got lucky this time: one node, no outage, replacements healthy. The cluster looked fine if you squinted at HTTP metrics. It didn't look fine if you counted evicted pods — and next time, that's the number I'll be watching before it hits ninety-seven again.