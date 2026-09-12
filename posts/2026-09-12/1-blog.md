# We tagged EKS workers like app servers — and Prometheus started scraping telegraf on nodes that never had it

The Telegraf Down alerts started piling up on a Thursday morning, and at first glance it looked bad. Nine targets, all critical, all under the same rule name. My first instinct was a fleet-wide agent failure — something in the monitoring stack had broken overnight and we were about to page half the platform team for a problem that didn't exist.

It wasn't that. It was worse in a quieter way: one alert name, at least three unrelated root causes, and one of them was our own governance work from three days earlier finally catching up with us.

## The tagging work nobody thought would touch monitoring

On September 8 we were in the middle of an org-wide AWS governance push — standard tags across prod VPCs for cost allocation, ownership, compliance, inventory. Same schema everywhere: `Application`, `Component`, `businessunit`, `environment`, `techteam`, `Role`, `Criticality`, and the rest. Multiple VPCs in `ap-south-1`, each with its own change ticket, but the rules were consistent.

We were careful about it. Add-only on instances and ASGs — never overwrite existing `Name`, `service`, `backup`, or legacy tags. For `Component`, `businessunit`, and `techteam`, if an instance already had a value, we kept it; VPC-wide defaults only filled gaps. VPC-level tags went on first (`Tech Owner`, ticket reference), then bulk instance tagging.

In one prod application VPC, that all went according to plan for the traditional stuff. Tomcat/Spring ASGs already had `techteam` set; we added `environment=prod` and the common governance keys without touching what was there.

The EKS application nodegroup ASG was different. Before September 8 it only carried EKS-managed tags — `eks:cluster-name`, `eks:nodegroup-name`, `k8s.io/cluster/*`. No `techteam`, no `environment`, no `Application`. The ASG-level script added `environment=prod` and the governance keys. `techteam` wasn't set at ASG level because our rule said use existing values only, and there wasn't one.

The running worker instances ended up with `techteam`, `Application`, `environment`, and `businessunit` anyway — likely from EKS nodegroup or launch template tagging tied to the same governance work, not from us replacing an old value. From a compliance perspective, that looked fine. From a monitoring perspective, we had just told Prometheus these were prod platform hosts.

## Why the alert fired three days later

Central Prometheus discovers host telegraf via EC2 service discovery. The job filters on `tag:environment=prod` **and** `tag:techteam` matching a regex of several platform team values. Scrape port `:9273`.

EKS worker nodes are EC2 instances. Once they picked up `environment=prod` plus a matching `techteam`, they entered the scrape pool. But Kubernetes workers don't run host telegraf on `:9273`. Metrics on those nodes come from in-cluster DaemonSets or cAdvisor — not a host agent listening on the standard port.

Five EKS worker targets went permanently `up=0`. Telegraf Down, critical. It looked like a sudden outage. It was a discovery side effect from September 8 governance work, surfacing in bulk once alert volume crossed whatever threshold made it impossible to ignore.

That was the story I wanted to be true — one cause, one fix, done by lunch. I started grouping targets by hostname and role before touching anything, which turned out to be the only reason we didn't make things worse.

## One alert, three root causes

Prometheus showed roughly nine telegraf targets down, plus one kafka exporter and one redis exporter. Same alert family, completely different problems underneath.

**EKS workers (5 hosts)** — tagging side effect. These nodes were never supposed to be in the EC2 SD scrape pool. They matched the tag filter after governance tagging. No telegraf process on `:9273` because that's not how we monitor Kubernetes workers. False positive, unfixed at the time we captured this.

**New AL2023 ASG instances (2 hosts)** — real telegraf misconfiguration, unrelated to EKS. Launched a few days before the alert spike. Telegraf RPM was installed, but the config was broken: `prometheus_client` output was commented out, so the agent logged "no outputs found" and had nothing to expose on the scrape port. Ansible-pull had never run on those boxes to template `telegraf.conf`. Fixes for AL2023 telegraf existed in the ansible repo; they just hadn't been applied to new ASG instances because there was no ansible-pull cron on those hosts.

**Kafka broker (`:9308`)** — long-standing debt, not a telegraf problem. The kafka exporter service had been disabled for months. Telegraf on `:9278` on the same host was actually fine. The alert rule conflated exporter health with agent health, or we were looking at the wrong port when we first opened the target list.

On top of those three, we also had a redis host with both telegraf and redis exporter down, and a dev/test host that probably shouldn't have been in the prod scrape config at all. Different owners, different fixes — all wearing the same alert costume.

I spent a while on the kafka broker before I noticed telegraf was healthy and the exporter was the dead component. Classic trap: one alert name makes you assume one failure mode. The AL2023 hosts took longer because the RPM was *there* — `systemctl status telegraf` looked plausible until you read the config and saw the commented output block. EKS was the fastest to classify once I checked tags and confirmed no listener on `:9273`.

## The fix we wanted vs. the fixes we didn't want

For the EKS issue, the least-change path was a Prometheus relabel drop on the telegraf EC2 SD job: drop targets where `eks:cluster-name` exists (or an equivalent EKS tag). Roughly four lines, config reload. No governance rollback, no new DaemonSet, no alert silence.

We explicitly ruled out a few alternatives:

- **Remove tags from the nodegroup** — rolls back compliance work for a monitoring problem. Wrong lever.
- **Install host telegraf as a DaemonSet on EKS** — large ops burden unless we actually need host-level metrics on workers, which we don't for this scrape job.
- **Silence the alert** — hides real failures on the AL2023 hosts and the kafka/redis issues.

For the AL2023 hosts, the real fix is ansible-pull (or equivalent) running the telegraf role so `prometheus_client` output gets templated correctly. That's ops work on two boxes, not a Prometheus change.

For kafka, re-enable the exporter after verifying cluster health — separate ticket, separate owner.

At the time we captured this, most of those fixes were still pending: Prometheus relabel for EKS nodes, ansible-pull on the AL2023 ASGs, kafka exporter re-enablement, and SSH access to diagnose the redis host.

## What I'd check before the next bulk VPC tag

Governance tags and monitoring discovery share the same key space. We use `environment` and `techteam` for cost and compliance; Prometheus EC2 SD uses the same keys to decide what to scrape. Those two systems don't talk to each other until an alert fires.

Before bulk tagging a VPC, I'd pull the EC2 SD jobs that filter on those tag keys and ask: will EKS nodes enter this pool? Will patch-automation orphans? Dev instances that happen to have `environment=prod` from a template copy? Tagging makes an instance *visible* to discovery; it doesn't install the agent discovery expects.

EKS workers are not app EC2. Tagging them like traditional Tomcat boxes makes Prometheus expect host telegraf on `:9273`. The nodes did nothing wrong. The tags were correct for governance. The scrape config was written for a different kind of machine.

And when nine targets go red under one rule name, classify by host role before you fix anything. We almost treated a compliance side effect, a config drift on new AMIs, and months-old exporter debt as a single incident. They're three. The alert didn't know that. We had to.

---

**Status at time of writing:** EKS relabel fix identified but not deployed; AL2023 telegraf pending ansible-pull; kafka exporter pending re-enable; redis host blocked on access. If you're reading this after those landed, the false positives should be gone and the real ones should be green — or at least owned by the right team.