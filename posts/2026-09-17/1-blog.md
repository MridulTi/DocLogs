# No official Storm Helm chart — how we put Apache Storm on EKS anyway

The Argo CD app for Storm had been red for two days, but the symptom that actually sent me down the rabbit hole was quieter than a crash loop: init containers on the Supervisor pods, stuck forever, printing the same line over and over — *waiting for nimbus …:6627*. No Nimbus, no workers, no UI. Just a cluster that looked almost deployed and wasn't.

We were trying to do something the organization had never done before: run Apache Storm on Kubernetes. Not a lift-and-shift of an existing pattern — there was no pattern. Storm still lived on traditional EC2/ASG elsewhere. The ask was to move it onto the same non-prod EKS cluster we were already standing up for the other application platform: Terraform, Karpenter, Argo GitOps, the whole stack. Streaming workloads sitting with everything else instead of a separate pet fleet.

That part made sense strategically. Operationally, it was a blank page.

## Why there was no paved road

Apache Storm does not ship a maintained official Helm chart. The project does not publish a credible "migrate Storm to Kubernetes" guide. Community options exist — G-Research's `gresearch/storm` chart with a Bitnami ZooKeeper subchart is the one people point at — but nothing we could treat as a supported product. We evaluated it and still built a thin local chart instead, same as other custom overlays in the repo: own the templates, own the values, no opaque upstream dependency.

That decision felt right and scary in equal measure. We were the first team anywhere in the org — any account, any region — putting Storm on Kubernetes. No internal reference architecture, no runbook, no "copy what prod did." Every choice about storage, networking, image choice, and GitOps layout was experimental. Before we committed, we wrote down what we were afraid of. That list turned out to be more accurate than our initial rollout plan.

We planned a phased rollout on purpose. Phase one: ZooKeeper and Nimbus only — prove the control plane and that PVCs actually bind. Phase two: Supervisors and Storm UI as stateless Deployments. Phase three: a LogViewer sidecar on supervisor pods, not a separate Deployment. Phase four: private ECR images instead of Docker Hub upstream. Phase five: Storm UI on the shared private ALB ingress pattern the rest of other already used.

One shared Storm namespace on the non-prod cluster, not one cluster per environment. Karpenter-provisioned ARM64 nodes. A StorageClass for `gp3` embedded in the Storm chart itself rather than a separate Argo Application — tradeoff being that chart prune would remove the class, but we avoided yet another GitOps app for a single consumer.

The architecture looked reasonable on paper:

| Component | Kind | Storage |
|-----------|------|---------|
| ZooKeeper | StatefulSet | PVC (data + datalog) |
| Nimbus | StatefulSet | PVC |
| Supervisor | Deployment | emptyDir; pod IP as `storm.local.hostname` |
| Storm UI | Deployment | emptyDir |
| LogViewer | sidecar on Supervisor | shared emptyDir `/logs` |

Reasonable, and completely untested in our environment.

## The cascade that wasn't obvious at first

When things broke, they did not break loudly. Failure chain number one was storage, and it propagated silently.

Our chart requested a StorageClass named `gp3`. The EBS CSI driver on the cluster was healthy. The StorageClass did not exist. The cluster only had legacy in-tree `gp2`. We had flagged this exact fear before rollout — "we feared silent PVC Pending forever" — and we were right.

PVCs for ZooKeeper and Nimbus sat in `Pending`. Without bound volumes, those StatefulSet pods never scheduled. Without Nimbus listening on `:6627`, everything downstream waited. Supervisor and UI init containers blocked on the nimbus health check. Argo marked the app Degraded. The StatefulSets showed OutOfSync because pods never became ready. From the outside it looked like a Storm problem. It was a storage class problem three layers down.

That was the first lesson in how StatefulSet failures hide: init containers do not scream "your StorageClass is wrong." They scream "upstream isn't ready yet," which sends you chasing Nimbus when Nimbus was never going to start.

We fixed the missing class — embedded `gp3` via EBS CSI in the chart — and the control plane could finally land. Then failure chain number two hit immediately, and this one was louder.

Nimbus crashed with:

```
/docker-entrypoint.sh: exec: nimbus: not found
```

Storm UI did the same for `ui`.

We had copied Helm examples that pass bare args like `nimbus` or `ui`, which works for upstream Docker Hub images. Our private ECR images use a `docker-entrypoint.sh` that execs the first argument as a command. They need `storm nimbus` and `storm ui`. Supervisors and the LogViewer sidecar already used the `storm …` form; Nimbus and UI did not. Official image docs do not apply when you own the entrypoint. We should have tested container startup before wiring the full chart, not after PVCs finally bound.

Fix was a one-line args change per deployment. The archaeology cost more time than the fix.

## Argo fighting StatefulSets, and the ALB that couldn't find a port

With pods actually running, we got failure chain number three: perpetual Argo sync drift on StatefulSet `volumeClaimTemplates`. Kubernetes injects `apiVersion`, `kind`, `volumeMode`, and `status` after create. Our chart templates did not emit the full schema Argo expected, so the app sat OutOfSync even when the cluster was fine. This is a known footgun with GitOps and StatefulSets. We fixed it two ways: corrected the chart templates to emit the full volumeClaimTemplate schema, and added `ignoreDifferences` jq paths with `RespectIgnoreDifferences` for the immutable VCT fields Argo will never reconcile away.

That one felt familiar if you've run StatefulSets under Argo before. The ingress problem did not.

Failure chain number four was AWS Load Balancer Controller weirdness exposing Storm UI. We wanted the same private ALB pattern as other other apps. LBC returned effectively: TargetGroup port is empty. We had Instance target type with a ClusterIP service — a combination that does not work the way we had it wired. Ingress backends need numeric ports with `target-type: ip`, not named ports with Instance mode. We switched to `target-type: ip` and backend port `8080` as a number, not a named service port. Storm UI came up behind the shared ALB.

Separately, we were migrating inbound access on that ALB from CIDR allowlists to security-group-based inbound. That affects every app on the load balancer, not just Storm. We added a parallel SG-based ALB config file so CIDR and SG ingresses could coexist during cutover testing rather than replacing the inbound model on a shared ALB before every consumer was validated.

## What we validated along the way

Not everything we worried about broke, but everything we worried about deserved an explicit check.

Stateful workloads on Karpenter made us nervous — ZK and Nimbus expect stable identity and disk; Karpenter nodes are ephemeral by design. For non-prod we accepted single-replica ZooKeeper with no quorum. HA in prod is still an open question.

ARM64 was non-negotiable on our Karpenter pool. Private ECR images are single-arch. If they had been amd64-only, we'd have seen scheduling failures or runtime crashes on Graviton. We verified arch before calling the rollout done.

Supervisor and LogViewer logs live on `emptyDir`. Pod restart means lost worker logs. Fine for non-prod exploration; scary for prod debugging. We noted it and moved on — durable log shipping is still TBD.

Topology lifecycle is also TBD. The chart runs the cluster; it does not submit topologies. How jar submit, worker scaling, and upgrades interact with Deployments versus traditional supervisor hosts — we haven't answered that yet. We kept topologies out of scope on purpose so we could fail fast on PVCs and images without dragging application deployment into the first week.

By the end of the week, all four failure chains were closed. Argo showed the Storm app healthy. We had the first Apache Storm cluster running on EKS in the organization: custom Helm, GitOps-managed, on Karpenter ARM nodes. ZooKeeper and Nimbus StatefulSets bound PVCs. Private images ran once we corrected entrypoints. Storm UI sat behind the same private ALB pattern as the rest of other.

## What I'd do differently, and what I'd tell the next team

If I were starting this again, I'd run a pre-flight checklist before the first `argocd app sync`, not after init containers had been waiting for forty-eight hours:

1. **StorageClass exists on the target cluster** — `gp3` via CSI is not the same as in-tree `gp2`. PVC Pending cascades silently through init containers.
2. **Container entrypoint behavior** — `docker run` with the exact args your Helm chart will pass, especially for private images. Do not assume `args: [nimbus]` from upstream examples.
3. **Argo + StatefulSet volumeClaimTemplates** — emit the full schema or configure `ignoreDifferences` upfront. You will hit VCT drift; budget for it in the chart, not as a week-two surprise.
4. **AWS LBC + ClusterIP** — `target-type: ip` and numeric backend ports. Named ports plus Instance mode gave us an empty TargetGroup port and a day of ingress debugging.

The bigger takeaway is about first-in-org workloads. No reference deployment means every assumption — ARM, storage, HA, logs, ingress models on shared infrastructure — has to be validated on the actual cluster. Writing down the fear inventory before we committed did not prevent the failures. It did prevent us from treating them as mysteries. We knew storage was a risk, entrypoints were a risk, Argo StatefulSet sync was a risk, ALB quirks were a risk. When each one fired, we recognized it instead of spiraling.

We still went forward for good reasons. Platform direction is Kubernetes; maintaining a separate Storm EC2 fleet alongside a new EKS cluster doubles operational surface — patching, AMIs, security groups, deploy pipelines. Non-prod first bounded blast radius. We reused GitOps muscle we already had with other apps, Alloy, Jenkins ingress. Phased delivery let us prove the control plane before workers and UI. Someone had to be first; better on non-prod with eyes open than a surprise prod migration later.

Prod cutover still has open questions: ZooKeeper HA with a three-node quorum on EKS, a topology submit pipeline from CI, supervisor horizontal scale and slot planning, durable log shipping, whether to adopt the community chart or keep the local one, DNS cutover from legacy Storm UI, and migrating the shared ALB fully to SG-based inbound after all apps are tested. None of those blocked non-prod stand-up. They are the next chapter.

Storm on Kubernetes is DIY. There is no official Helm chart and no migration guide. Budget time for chart authorship and image entrypoint archaeology. And when init containers say they're waiting for Nimbus, check whether Nimbus ever had a chance to start — the bug might be three layers below Storm itself.