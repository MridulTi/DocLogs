**Phase 1 — LinkedIn draft (from your template)**

---

**Option A — Short (recommended)**

One alert. Three different root causes.

After an org-wide AWS governance tagging push, our central Prometheus started treating EKS worker nodes like traditional app servers — and tried to scrape host Telegraf on a port that was never there. Five false “Telegraf Down” criticals looked like an outage. They weren’t.

Digging in, we found the tagging side effect was only part of the story: new AL2023 instances had Telegraf installed but misconfigured, and a Kafka broker had a long-standing exporter gap masked by the same alert rule.

**Impact:** We separated compliance work from real monitoring debt and defined a least-change fix — relabel EKS nodes out of the EC2 scrape pool — without rolling back governance tags.

**Lesson:** Tags used for cost and compliance can silently change what your observability stack discovers. Before bulk tagging a VPC, ask: *who enters the scrape pool now?*

---

**Option B — Slightly longer / story arc**

We didn’t break production. We broke how Prometheus *found* production.

During a standard governance tagging rollout — same tag schema across prod VPCs, add-only on instances — EKS worker nodes picked up `environment=prod` and team tags they’d never had before. Central Prometheus uses those exact tags for EC2 service discovery. Suddenly, five Kubernetes workers landed in a Telegraf scrape job meant for Tomcat/Spring hosts on `:9273`.

Workers don’t run host Telegraf there. Metrics come from in-cluster paths. Result: permanent `up=0` and a spike of critical alerts that *felt* like a sudden outage.

The twist: one alert name hid three unrelated problems — EKS discovery noise, broken Telegraf config on newer AL2023 ASGs, and a disabled Kafka exporter on a broker that had been quiet for months.

**Outcome:** Clear classification, clear fixes. Drop EKS nodes via relabel (keep the tags). Fix real Telegraf/ansible gaps on the ASG hosts. Re-enable Kafka exporter after a health check. No compliance rollback.

**Takeaway for platform teams:** Governance tags and monitoring filters often share the same keys. Align them *before* bulk apply — or your next “incident” might just be good compliance work surfacing in the wrong dashboard.

---

**Hashtags (optional, pick 2–4)**

`#DevOps` `#SRE` `#Observability` `#Kubernetes` `#AWS` `#PlatformEngineering`

---

**Sanitization notes (already applied in drafts)**

- No account IDs, hostnames, or internal team regex values  
- No ticket/Jira references  
- Framed as learning, not blame  

Want a **more technical** version (with a tiny relabel snippet) or a **leadership-focused** version (compliance vs. observability alignment)? I can draft Phase 2 in that tone.