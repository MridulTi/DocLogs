# When `/var/tmp` forgot our Kafka directory

The alert wasn’t dramatic. REST on **8083** answered fine, the connector showed **RUNNING**, and then I pulled task status and saw **`FAILED`** with a stack trace long enough to scroll past three screens. Patch night had been **2026-10-08** — kernel **6.1.188-233.386**, reboot around **16:10 UTC** (**21:40 IST**). We were triaging around **22:18 IST** the same evening. Telegraf had been complaining about Jolokia every fifteen seconds. Two separate problems were shouting at once; only one of them was actually stopping records from leaving the worker.

## What we were looking at

This is a distributed **Kafka Connect** worker on an AL2023-style host: Connect REST on **8083**, source connector with a **producer override** forcing **`zstd`** compression. The unit file pins the JVM temp directory on purpose:

```text
JAVA_TOOL_OPTIONS=-Djava.io.tmpdir=/var/tmp/kafka
```

That’s a reasonable choice — keep Kafka’s temp junk out of `/tmp` and give it a known path. What we hadn’t wired up was anything that **recreates** `/var/tmp/kafka` after a reboot. The package didn’t drop a `tmpfiles.d` snippet; the systemd unit had no `ExecStartPre` to `mkdir` and `chown`. On paper the connector was healthy until the first time the task tried to **produce** with zstd. Startup doesn’t touch zstd-jni; the failure waits for the data path.

A sibling worker in the fleet had the same hole — same unit pattern, same missing directory after reboot. This wasn’t one corrupted tarball or a broker outage.

## Following the stack, not the noise

I started where Connect always sends you: status over REST. Connector **RUNNING**, task **FAILED**. The abbreviated trace looked like a generic `ConnectException` around `sendRecords`, then:

```text
org.apache.kafka.connect.errors.ConnectException: ... sendRecords ...
Caused by: java.lang.NoClassDefFoundError:
  com.github.luben.zstd.ZstdOutputStreamNoFinalizer
Caused by: java.lang.ExceptionInInitializerError:
  Cannot unpack libzstd-jni-1.5.6-10: No such file or directory
Caused by: java.io.IOException at File.createTempFile(...)
```

My first instinct was classpath or a bad Connect install — `NoClassDefFoundError` often means “jar missing.” But the message wasn’t “class not found” in the usual sense; it was **cannot unpack** and **`File.createTempFile`**. That’s native code landing on disk, not a missing Maven artifact.

We’d set `producer.override.compression.type=zstd` on this connector. Cluster `producer.properties` might still say `none`; the override is what matters here. ZSTD in the Kafka client goes through **zstd-jni**, which unpacks a platform-specific library into **`java.io.tmpdir`** on first use. If that directory doesn’t exist, `createTempFile` throws, the static initializer for the zstd classes fails, and every later compress attempt dies with `NoClassDefFoundError`. REST stays up; Debezium/MySQL wasn’t the story — local JVM, tmpdir, compression.

I checked the path we’d told the JVM to use:

```bash
ls -ld /var/tmp/kafka
```

No such file or directory. **`/var/tmp` is often tmpfs** on these images. Reboot wipes it. We’d rebooted for the kernel patch; Connect came back with `java.io.tmpdir=/var/tmp/kafka` pointing at air.

That also explained why it felt “still broken after restart.” Restarting Connect **without** creating the directory first just boots another JVM into the same wall. Restarting **only** the connector task doesn’t help if the process already tripped the initializer — and REST can keep serving a **stale `trace`** on FAILED tasks. I learned to trust **`tasks[0].state`** and fresh **`connect.log`**, not only the trace blob in JSON.

Quick verify when you’re in a hurry:

```bash
curl .../connectors/<id>/status | jq '.tasks[0].state'
```

## The red herring on port 8778

While I was on the box, Telegraf was logging:

```text
[inputs.jolokia2_agent] unable to gather metrics for http://localhost:8778/jolokia
dial tcp 127.0.0.1:8778: connect: connection refused
```

Easy to lump that in with “Connect is sick.” It wasn’t. `ss` showed **7073** and **8083** listening; **nothing on 8778**. Telegraf still had **`jolokia_jmx.conf`** aimed at Jolokia; the Connect unit was running **JMX Prometheus** on **7073**, not Jolokia. **8778** lived only in monitoring config. Metrics gap and log noise — not the failed task. I kept the data-path fix separate from “fix Telegraf or scrape 7073 properly.”

Side note on timestamps: EC2 `last reboot` and `uptime -s` are often **UTC**. Telegraf lines with **`…Z`** are UTC. I was thinking in IST (**+05:30**); mixing those without converting makes the timeline lie.

## What actually fixed production

On the affected worker, during the investigation:

```bash
mkdir -p /var/tmp/kafka
chown kafka:kafka /var/tmp/kafka
chmod 1770 /var/tmp/kafka
systemctl restart kafka-connect
```

If the task was still **FAILED** after the process had a real tmpdir:

```bash
POST .../connectors/<name>/tasks/0/restart
```

After that: task **RUNNING**, logs showed normal streaming and successful sends. Downstream lag on that pipeline shard had been the real impact — source couldn’t produce until the directory existed.

For something that survives the **next** patch reboot, the durable fix is **`tmpfiles.d`**:

```text
# /etc/tmpfiles.d/kafka-connect.conf
d /var/tmp/kafka 1770 kafka kafka -
```

Then `systemd-tmpfiles --create` (or reboot and let tmpfiles run). Optional belt-and-suspenders in **`kafka-connect.service`**:

```ini
ExecStartPre=/usr/bin/mkdir -p /var/tmp/kafka
ExecStartPre=/usr/bin/chown kafka:kafka /var/tmp/kafka
```

If we manage these hosts with Ansible or similar, the mkdir and ownership belong in the role — not a post-reboot ritual someone remembers once and forgets twice.

The other lever, if we wanted to dodge zstd-jni entirely: change `producer.override.compression.type` to **`lz4`**, **`snappy`**, or **`none`**. You trade compression ratio and CPU for not depending on native unpack into a directory ops forgot to create. We kept zstd and fixed the directory.

Telegraf/Jolokia is a different ticket: drop or replace the 8778 input, scrape **7073** with a Prometheus-compatible input, or align JVM agents with what monitoring expects. I didn’t confirm fleet-wide rollout of `tmpfiles.d` or a clean Telegraf migration on every Connect worker — those were the open gaps when we closed the incident on the broken host.

## What I’d check first next time

After any Connect host reboots: **`ls -ld /var/tmp/kafka`** before you spend an hour on brokers or connector plugins. If you use **`JAVA_TOOL_OPTIONS=-Djava.io.tmpdir=...`**, that path has to exist **before** the JVM starts, every boot. ZSTD on Connect means zstd-jni means natives under tmpdir — full stop.

Same week, another node taught a different lesson (**Java 8 vs 17**, `UnsupportedClassVersionError`, unset **`JAVA_HOME`** in systemd). Different failure mode, same theme: the unit and env file are part of the system, not decoration.

I’ll remember **7073** (Prometheus JMX) vs **8778** (Jolokia) so I don’t chase connection refused on a port we never opened. And I’ll convert log timestamps before I tell the story in IST. The bug was boring — a missing directory on tmpfs. The stack trace wasn’t.