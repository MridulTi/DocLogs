Here’s a concise LinkedIn draft from your evidence:

---

**Prod Kafka at 100% disk — and we couldn’t expand the volume**

Last week we hit a production incident: two of three Kafka brokers had `/data` at 100% (~850G used, ~20K free). EBS resize wasn’t an option at the time, so manual cleanup was off the table.

The first instinct was consumer lag. Lag was low (~262). Only 2 of 7 Logstash instances were on the topic — worth fixing, but not the root cause.

The real issue was retention: 48h time-based retention with no byte cap on a high-volume log topic (40 partitions, ~30G per partition). Segments kept accumulating for two full days regardless of how fast consumers ran.

**What we did instead of risky manual deletes:**
- Tighten `retention.ms` (e.g. 24h) and set `retention.bytes` per broker so delete-policy could reclaim space safely  
- Pause or scale down producers briefly if needed before changing retention  
- Scale Logstash consumption as follow-up, not as the primary fix  

**Outcome:** Avoided manual segment deletion on prod, identified retention policy as the root cause, and had a clear path to free disk without a volume resize.

**Takeaway:** Low consumer lag doesn’t mean a healthy broker. On log-heavy topics — especially ones fed by Kubernetes log shippers — always check `retention.ms` *and* `retention.bytes` when `/data` fills up.

#Kafka #DevOps #SRE #IncidentResponse #ProductionEngineering

---

**Optional shorter version** (if you prefer a tighter post):

---

Prod Kafka: 100% disk, volume can’t be expanded, lag looks fine.

Turns out 48h retention with no byte cap on a high-volume log topic was filling brokers — not slow consumers.

We fixed it by tightening retention config so delete-policy could reclaim space safely, without manual cleanup on prod.

Lesson: on log-heavy topics, check retention policy, not just consumer lag.

#Kafka #SRE #DevOps

---

Want a version with more technical detail, or one framed more as a leadership/team story? I can adjust tone or length.