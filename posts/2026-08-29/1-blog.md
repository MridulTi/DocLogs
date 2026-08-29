# When Kafka Hits 100% Disk and the Volume Won't Grow

The alert didn't come from consumer lag. It came from disk — two of three brokers on our production Kafka cluster reporting `/data` at 100%, with about 20K free on an 850G EBS volume. That's not "we should look at this tomorrow" territory. That's "something is about to stop accepting writes" territory.

We couldn't expand the volume. Not "we'd prefer not to" — the EBS volume literally wasn't modifiable at that moment. So the usual playbook — bump the disk, watch the graph flatten — was off the table. Whatever we did had to reclaim space from inside Kafka itself, without casually deleting segments on prod.

## What we were looking at

This is a three-broker cluster in production. The pain was concentrated on a high-volume log topic: 40 partitions, replication factor 2, fed by Kubernetes log shippers. Three consumer groups were attached. On paper, consumption looked fine — lag was around 262, which is nothing you'd page on.

Two brokers were pinned at 100%. The third still had headroom, which told us this wasn't a uniform cluster-wide misconfiguration; it was a retention and placement problem playing out unevenly across replicas.

The topic config, when we pulled it:

```
retention.ms=172800000        # 48 hours
retention.bytes=-1            # no byte cap
segment.bytes=536870912       # 512MB segments
compression.type=producer
```

Forty-eight hours of retention with no byte limit on a topic that ingests K8s logs at scale. That's the kind of config you set once during bootstrap and never revisit until `/data` screams.

## Starting with the obvious — and ruling things out

First instinct: consumer lag. Maybe Logstash fell behind and segments aren't getting cleaned up because consumers haven't committed offsets far enough?

We checked. Lag was ~262. Consumers were keeping up. That dead end mattered — it kept us from burning time scaling consumers as the primary fix. (More on Logstash later; it was a follow-up, not the root cause.)

Next: how big is this topic actually?

```bash
du -sh /data/kafka-logs/<topic>-*
```

Roughly 30G per partition. Forty partitions, RF=2 — the math adds up fast. Even with compression (`producer`), you're holding two days of high-volume log traffic with no ceiling on total bytes. The disk didn't fill because consumers were slow. It filled because retention policy said "keep everything for 48 hours, however big that gets."

I also briefly entertained a storage hack: attach a third EBS volume and use `growpart` to extend the existing 850G disk. That doesn't work the way I wanted it to — you can't just bolt on block storage and grow an existing filesystem across unrelated volumes. Ruled out before anyone got too excited about it.

At this point the picture was clear: **time-based retention with no byte cap on a firehose topic**. Segments age out on the clock, not on disk pressure. Low lag doesn't help if you're still obligated to retain 48 hours of data regardless of volume.

## Why two brokers and not three

With RF=2 on 40 partitions across three brokers, replica distribution isn't perfectly even. Leader election and partition assignment meant two brokers ended up holding more of the heavy replicas. The third broker had room — which is almost worse, because it makes the incident look like a broker problem when it's really a topic policy problem showing up asymmetrically.

Running diagnostics locally had its own friction. One broker had bootstrap connection quirks when I tried to run `kafka-configs` from my laptop — enough to slow me down, not enough to change the diagnosis. I didn't capture the exact error string, but it was the kind of thing where you SSH to the broker and run the command there instead of fighting client config for twenty minutes during an incident.

## The fix we could actually do in prod

Manual log deletion on a prod cluster is a last resort. You can orphan consumers, confuse leaders, and create a very exciting afternoon for everyone. We needed Kafka's delete policy to do the work — which meant changing retention so old segments become eligible for cleanup.

The prod-safe path:

**1. Tighten `retention.ms`** — we targeted 24h instead of 48h. Halving the time window doesn't instantly free 850G, but it changes which segments are eligible for deletion on the next cleanup cycle.

**2. Set `retention.bytes`** — this was the important half. Per-broker byte limits give the delete policy something to act on when time alone isn't enough. With `-1`, Kafka had no reason to drop data early regardless of disk pressure.

Something like:

```bash
kafka-configs --bootstrap-server <broker> \
  --entity-type topics --entity-name <log-topic> \
  --alter --add-config retention.ms=86400000,retention.bytes=<per-broker-cap>
```

The exact byte cap needs to fit your partition count and RF — you're budgeting across replicas, not pretending one broker owns the whole topic. I don't have the final number we landed on in my notes, but the principle was: set a cap that forces segment deletion before `/data` hits 100% again, with headroom for normal variance.

**3. Pause or scale down producers if needed** — before flipping retention on a full disk, you sometimes need to stop the inbound firehose briefly. K8s log shippers don't care about your incident; they'll keep writing. Reducing producer pressure before the config change gives the delete policy room to catch up instead of fighting new segments while old ones are still technically retained.

**4. Watch segments actually disappear** — this isn't instant. Cleanup runs on a schedule. We monitored `/data` free space and confirmed segments aging past the new retention window were getting removed. No manual `rm -rf` in the log directories.

## Logstash — real problem, wrong root cause

Only 2 of 7 Logstash instances were consuming this topic. That's worth fixing. Under-provisioned consumption can cause lag, can cause operational blind spots, and is generally sloppy.

But lag was 262. The disk was full because retention said "keep 48 hours, unlimited size." Scaling Logstash would improve throughput and resilience; it would not have emptied an 850G volume holding two days of unrestricted log data. We flagged it as follow-up work, not incident mitigation.

That's a distinction I want to keep sharp: **healthy-looking lag masked an unhealthy retention policy**. I've seen teams chase consumer scaling during disk incidents before. Sometimes that's right. Here it would've been a distraction.

## What I'd do differently

I'd have caught this before `/data` hit 100%. Disk usage per broker and retention config on high-volume topics belong in the same dashboard. Lag alone is a lie of omission when `retention.bytes=-1`.

If I couldn't resize the volume during the incident, I'd still open the ticket to make it resizable — storage headroom isn't a substitute for correct retention, but running prod Kafka with no expansion path is its own risk.

Next time I'd also verify Logstash consumer coverage during topic onboarding, not during a disk emergency. Two of seven is a config drift problem waiting to happen.

---

**Takeaways from this one:**

- Low consumer lag does not mean disk is healthy. Check `retention.ms` *and* `retention.bytes` when `/data` fills on log-heavy topics.
- K8s log shippers feeding Kafka can fill brokers even when every consumer group looks caught up — the firehose doesn't care about your lag graph.
- When you can't expand the volume, your only safe lever is retention policy. Set byte caps before you need them.