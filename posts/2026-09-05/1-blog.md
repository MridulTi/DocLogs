# Standing up a greenfield EKS cluster — and every mistake we stepped on

The Argo CD UI showed `SyncFailed` on `karpenter-node-infra` before we'd deployed a single application pod. `EC2NodeClass` and `NodePool` didn't exist in the cluster — not because the manifests were wrong, but because the CRDs had never been installed. We'd already burned an afternoon on Terraform provider pins and ARM AMI mismatches. This was supposed to be the easy part: GitOps bootstrap, Karpenter online, move on.

It wasn't.

## What we were building

We weren't cloning a legacy self-managed K8s 1.21 ASG stack. This was a greenfield non-prod EKS cluster in an existing VPC — private API only, VPN/office CIDRs on the cluster security group, subnets tagged for cluster shared ownership, internal ELB, and `karpenter.sh/discovery`.

The compute model had two layers on purpose:

**Layer 1** — a bootstrap managed node group: on-demand ARM64, AL2023, `t4g.xlarge`-class instances, min 1 / max 3, tainted `CriticalAddonsOnly=true:NoSchedule`. It runs Karpenter controller, Argo CD, EKS addons, and optionally Cluster Autoscaler scoped only to that ASG.

**Layer 2** — Karpenter NodePool for application workloads, with a separate EC2NodeClass and IAM role.

We chose Karpenter over Cluster Autoscaler for app scaling, EKS Pod Identity (not IRSA) for Karpenter/LBC/CA auth, Terragrunt for backend/provider DRY, `terraform-aws-modules/eks` ~20.36, and a dedicated GitOps branch. Target Kubernetes version: **1.36** on create — destroy/recreate, not an upgrade ladder on an empty cluster.

That all sounded clean on paper.

## Terraform got mean before the cluster existed

The first `terraform plan` failure was the AWS provider. We'd drifted to provider 6.x; EKS module 20.x still references launch template fields that 6.x removed. Plan blew up with errors about fields that no longer exist. Fix was blunt: pin `hashicorp/aws >= 5.40, < 6.0` alongside the module version and document the upper bound next time we bump either one.

Then architecture assumptions collided with reality. We started with spot on the bootstrap pool; requirement clarified to **100% on-demand**. Fine — but we'd already baked spot into early config. More annoying: we paired an **ARM64 AMI** with **x86 instance types**. AMI architecture has to match the instance family. Obvious in hindsight, expensive when you're staring at nodes that never join correctly.

The managed node group apply failed when AWS still had `desired=0` while we set `min_size=1`. The EKS module ignores `desired_size` after create — so on first create you have to set min/desired/max together, or manually bump desired ≥ min once before apply. I didn't know that until apply failed.

Disk was another silent lie. Module defaults said `disk_size=50`, but instances came up around **20 GiB**. The module default doesn't always win against the launch template path we were on. We needed explicit `block_device_mappings` on the bootstrap launch template — 50 GiB gp3 root — to get what we thought we'd already configured.

IAM role `name_prefix` exceeded **38 characters**. Set a short explicit `iam_role_name` on the node group instead of letting Terraform generate something too long.

We pinned the AL2023 ARM AMI via data source to `cluster_version`, not "latest surprise AMI." Addons in order: pod-identity-agent before compute, then coredns, vpc-cni, kube-proxy, ebs-csi. Karpenter got its node role, instance profile, access entry, and controller Pod Identity association in Terraform — which almost caused a duplicate IAM role later when GitOps still pointed at IRSA from a reference cluster. More on that.

One dead end I won't repeat: `CONTAINER_RUNTIME=docker` on AL2023 / K8s 1.32+. Invalid. Dockershim is gone. **containerd via nodeadm** is the correct path on AL2023.

## GitOps: where reference configs go to die

We copied a reference GitOps branch without scrubbing it. Wrong cluster names, IRSA ARNs, Karpenter version mismatched to our K8s version. I almost created a **duplicate Karpenter controller IAM role** — Terraform already had Pod Identity wired up, but Helm values still carried IRSA annotations from the old cluster.

Argo CD itself went on the bootstrap nodes with tolerations for `CriticalAddonsOnly`. Helm install first, then a Git deploy key secret — pods don't have `SSH_AUTH_SOCK`, so SSH agent forwarding wasn't an option.

Bootstrap order we settled on:

1. Argo CD on bootstrap nodes  
2. Git deploy key  
3. `karpenter-crds` app (sync wave -1) — CRDs from chart `crds/` dir, ServerSideApply  
4. Karpenter controller (`skipCrds: true`)  
5. `karpenter-node-infra` — EC2NodeClass + NodePool manifests  

That order exists because of a Helm behavior that's easy to miss: **`helm template` skips the chart `crds/` directory**. The controller chart never installed NodePool/EC2NodeClass CRDs. Argo kept reporting SyncFailed until we split CRDs into their own Application.

We made it worse before we made it better. **Two Argo apps owned the same CRDs**, and we had **argo-cd self-sync** enabled. Sync deadlock. CRD ownership has to be exactly one Argo app; the controller must use `skipCrds: true`. And the Application for `argo-cd` itself should **not** auto-sync — that's another path to deadlock.

`valueFiles: ../../helm-values/...` failed with parent path escape — Argo blocked it, charts rendered empty. Fix: multi-source with `ref: values`, or keep values under paths Argo allows inside the chart tree.

Bootstrap node sizing bit us too. `t4g.large` was too small for Argo + Karpenter + all system addons. We bumped to **xlarge** and stopped fighting eviction loops on the control plane of our control plane.

## The Karpenter vs Cluster Autoscaler confusion

Mid-build someone asked why Cluster Autoscaler wasn't adding nodes for pending app pods. Because **app capacity is Karpenter's job**, not CA's. We scoped CA to the bootstrap ASG only — optional, and only for that tainted pool. Pending app workloads need a healthy NodePool, EC2NodeClass, and Karpenter controller — not CA scale-out.

That question was a signal we'd documented the two-layer model in Terraform but not clearly enough in runbooks.

## Version path we shouldn't have taken

On an empty cluster we walked 1.31 → 1.32 → 1.34 → 1.36 instead of targeting **1.36 upfront** and destroy/recreating once. Greenfield means you pick the version before first apply, not ladder upgrades on nothing.

## The repo-server red herring

After a bootstrap node recycle, Argo showed `ComparisonError` and repo-server connection refused. I spent time suspecting chart bugs. Stale comparison state. Once bootstrap pods were healthy again, **refresh** cleared it — not a chart fix, not a Git problem.

## What actually worked

When we stopped fighting copied config and pinned the boring stuff:

- Terraform: provider `< 6.0`, explicit gp3 50 GiB on launch template, min/desired/max aligned on first NG create, Pod Identity for Karpenter/LBC/CA, short IAM role names, AMI arch matched to Graviton instance types.  
- GitOps: skeleton branch scrubbed for cluster name, discovery tag, Pod Identity vs IRSA, Karpenter version for K8s 1.36. Single CRD owner app with ServerSideApply. Controller with `skipCrds: true`. No auto-sync on argo-cd self-management.  
- Runtime: xlarge bootstrap nodes, on-demand only, containerd via nodeadm on AL2023.

End state: private control plane, Pod Identity auth, GitOps-ready Karpenter scaling, system controllers isolated from app workloads on a repeatable greenfield pattern.

## What I'd do differently next time

I'd treat the pre-apply checklist as blocking, not advisory:

- Confirm on-demand vs spot, ARM vs x86, target K8s version **before** first `terraform apply`.  
- Size bootstrap for Argo + Karpenter + all addons — start at xlarge.  
- Document the EKS module `desired_size` ignore behavior and set all three sizing knobs together on create.  
- Pin AWS provider upper bound whenever we pin EKS module version.  
- GitOps from a skeleton, never a fork — scrub names, discovery tags, Pod Identity vs IRSA, Karpenter/K8s version alignment.  
- CRD ownership: one Argo app, controller skips CRDs, argo-cd app doesn't auto-sync.  
- `valueFiles`: stay inside allowed paths or use multi-source values refs.

The cluster came up fine in the end. The story isn't "EKS is hard" — it's that greenfield gives you freedom to skip legacy baggage and still step on every sharp edge if you copy someone else's YAML without reading it. We learned more from the SyncFailed CRDs and the provider 6.x plan failure than from the architecture diagram. That's probably how it should be.