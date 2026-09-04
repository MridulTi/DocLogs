**Phase 1 — LinkedIn draft** (from your template + sanitized evidence)

---

**Standing up a greenfield EKS cluster — and learning what the docs don’t spell out**

We recently brought a new non-prod EKS cluster online: private control plane, GitOps from day one, and a clean split between **system** workloads and **application** scaling.

**The approach**
- **Layer 1:** A small bootstrap node pool (on-demand ARM64, AL2023) for Karpenter, Argo CD, and core addons — tainted so app pods don’t land there by accident  
- **Layer 2:** Karpenter NodePools for everything else — separate infra, separate IAM, scale when apps need it  
- **Terraform + Terragrunt** for the foundation; **Argo CD** for what runs on top  
- **EKS Pod Identity** instead of IRSA for controllers — simpler wiring for a greenfield stack  
- Target **Kubernetes 1.36 on create** rather than stepping through upgrade ladders on an empty cluster  

**What actually moved the needle**
A repeatable pattern: system controllers stay predictable and isolated; app capacity scales with Karpenter; new clusters can follow the same playbook instead of copying legacy self-managed setups.

**What cost us time (the human part)**
- AMI architecture has to match instance family — learned that the hard way  
- Provider/module version coupling: a major AWS provider bump broke `terraform plan` until we pinned versions  
- GitOps from a reference branch without scrubbing cluster names, auth mode, and Karpenter versions  
- Karpenter CRDs need their own install path — `helm template` skips `crds/`; one Argo app owns CRDs, controller uses `skipCrds: true`  
- Bootstrap nodes need to be sized for Argo + Karpenter + addons from the start — “large” wasn’t enough  

**Takeaway**
Greenfield is the right moment to decide: on-demand vs spot, ARM vs x86, target K8s version, Pod Identity vs IRSA, and CRD ownership — **before** the first `terraform apply`. The architecture is straightforward; the edge cases are where the calendar goes.

If you’re planning a similar build, I’m happy to swap notes on bootstrap sizing, Karpenter + GitOps ordering, and the checklist we wish we’d had on day one.

#Kubernetes #EKS #Terraform #GitOps #PlatformEngineering #DevOps

---

**Checkpoint:** This draft hits impact, challenge/solution, and outcome focus without internal names, ARNs, or account details.

Want a **shorter** version (~120 words), a **more technical** one for platform engineers, or a **“lessons learned”** hook for a follow-up blog post?