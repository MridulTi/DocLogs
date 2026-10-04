# When the cluster looked idle but nothing would schedule

The first thing I checked was the obvious one: CPU. Our non-prod EKS workers are Karpenter-managed, and application pods had been sitting in **Pending** long enough that Istio and app syncs were backing up. `kubectl top nodes` looked almost embarrassingly healthy — low CPU, memory in a comfortable band. If you squinted at the dashboard, you'd swear we had room.

Karpenter disagreed. Its logs kept repeating the same line:

```
Failed to schedule pod, all available instance types exceed limits for nodepool (NodePool=ec2nodepool)
```

So we weren't out of EC2 capacity in the abstract sense. We were out of **permission** to launch another node under the NodePool's own limits. That distinction cost us a good hour of false confidence.

## What we were actually running

The primary app pool (`ec2nodepool`) provisions Graviton workers through Karpenter. Limits and instance rules live in GitOps — in our case `helm-values/karpenter/nodepool.yaml`. The pool is meant to scale on demand in a handful of AZs, with requirements that steer toward arm64 on-demand instances.

Pending workloads weren't tiny sidecars. The pattern we kept seeing was on the order of **~700m CPU** and **~2Gi memory** per pod — normal for the services we were rolling. The Kubernetes scheduler places pods using **requests**, not what `top` shows as live usage. Karpenter, when it decides whether it may add a node, charges the **full EC2 instance shape** against the NodePool's `limits`, not remaining allocatable on existing nodes and not `kubectl top`. Two different accounting systems, both ignoring the graph that made us feel better.

## Following the scheduler first (dead end)

I started where I always start: why won't the scheduler bind this pod?

```bash
kubectl describe pod <pending-pod>
```

Events pointed at insufficient resources on existing nodes — CPU and memory **requested** by already-running pods had eaten the schedulable slack. That part made sense. What didn't make sense was why Karpenter wasn't replacing "full" with "add another node." The NodePool should scale out.

So I pulled Karpenter controller logs and hit the `exceed limits` message. That sent me to the NodePool object:

```bash
kubectl get nodepool ec2nodepool -o yaml
```

The `limits` section in Git matched what was live:

```yaml
limits:
  cpu: "80"
  memory: 80Gi
```

I'd read `limits.cpu: "80"` wrong in my head more than once over the years — it's **80 vCPUs** across the pool, not `80000m` millicores. The memory side was **`80Gi` total counted capacity**, same idea: sum of instance sizes Karpenter has already brought into this NodePool, not utilization.

At investigation time we had roughly **16 Graviton c6g nodes** — about eleven `large`, about five `xlarge`. Pool accounting had already consumed on the order of **~42 CPU** and **~79Gi** of kube-reported memory capacity against those caps. CPU still had headroom under 80. Memory did not. We had something like **~1.2Gi** left under the 80Gi ceiling.

A new **`c6g.large`** needs on the order of **~3.7Gi** of that counted capacity. Every instance type our requirements allowed was "too big" for the remaining memory budget. Karpenter couldn't launch *anything*, so pending pods stayed pending. Meanwhile `kubectl top` still showed nodes at low CPU% — because nobody was getting scheduled onto new capacity that didn't exist.

That was the first layer of root cause: **memory limit set as if it were symmetric with CPU, but instance charging is asymmetric on a c6g-heavy fleet.**

## The second layer: we only allowed two shapes

While staring at `nodepool.yaml`, the `requirements` block explained why Karpenter couldn't work around the squeeze.

We had pinned:

```yaml
# simplified from requirements
- key: node.kubernetes.io/instance-type
  operator: In
  values: [c6g.large, c6g.xlarge]
```

(I'd also seen a malformed empty string in that value list at one point — the kind of typo that makes you distrust every other line in the file.)

Broader rules in the same manifest talked about **instance-category** in **r, c, t** and arm64 on-demand, but the **instance-type** requirement overrides that story. Only those two c6g sizes could ever launch. When the pool brushed the memory ceiling, Karpenter couldn't say "fine, bring a different arm64 on-demand size with a better CPU/memory fit." It could only try c6g.large or c6g.xlarge, watch them fail the limit math, and log `exceed limits` again.

We briefly wondered about AZ capacity — real problem, different error shape. This one was self-inflicted config plus accounting.

## The fix and why it works

We fixed it in GitOps, two deliberate changes.

**Raise memory limit without touching the CPU cap we still wanted.** We moved `limits.memory` from **80Gi** to **160Gi** and left **`limits.cpu: "80"`**. The intent of the CPU cap stayed: an 80-vCPU arm pool. On this fleet, c6g-ish shapes run roughly **~1.9Gi kube memory capacity per vCPU** in the way Karpenter counts them. Pinning memory at 80Gi meant we'd hit the memory ceiling long before we could ever use the CPU budget — every extra c6g node was a memory tax toward the limit, not a proportional CPU tax. **150–160Gi** is the band that actually lets an 80-core pool breathe on c6g-heavy mixes; we picked **160Gi**.

**Remove the hardcoded `node.kubernetes.io/instance-type` requirement** so Karpenter can choose among on-demand **arm64** instances in categories **r, c, and t**, with **instance-generation > 4**, in the AZs we already configure. That restores the point of category-based requirements: when one shape doesn't fit the limit math or the pod mix, another generation-5+ arm instance might.

One footnote we wrote down for later: **`instance-generation > 4` excludes t4g** (generation 4). If we ever want burstable t4g in this pool, we'd relax generation — e.g. `Gt: "3"` to include 4 — instead of wondering why t4g never appears.

Rollout was the usual GitOps path: sync the Karpenter NodePool manifest through the cluster app, then verify:

```bash
kubectl get nodepool ec2nodepool
```

Watch pending pods clear and Karpenter provisioning events. The symptom triad we'd bookmarked — **Pending pods + `exceed limits` + healthy-looking `top`** — should break as soon as counted memory headroom and instance flexibility match reality.

## What I'd do differently

I won't trust idle-looking nodes on a Karpenter pool again without translating **limits** into **sum of instance sizes already in the pool**. Utilization and allocatable slack are real for the scheduler; they don't gate Karpenter's launch decision the same way.

And I'd treat **instance-type pins** as incident bait: fine for a lab, dangerous on a production NodePool unless you have a spreadsheet proving every allowed shape survives your limit math at max scale.

We had unrelated noise afterward — admission webhook timeouts on mesh components can still block pod creation even when nodes exist — so "Pending" isn't always one root cause. For this incident, though, the story was memory limits charged like CPU limits, and a two-size cage when we needed room to pick a better fit.

**Remember:** `limits.cpu: "80"` is eighty cores. NodePool limits are **inventory**, not **usage**. When Karpenter says everything exceeds limits, check memory counted against the cap before you chase AWS capacity — and read the instance-type requirements before you assume the autoscaler has options.