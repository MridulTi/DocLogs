# LinkedIn post (from your template)

---

**After a routine OS patch and reboot, our Kafka Connect pipeline went quiet — but the broker was fine.**

The connector showed RUNNING while the task was FAILED. The stack trace pointed at zstd compression and a missing native library unpack — classic red herring until we looked at the JVM.

**The challenge:** We’d set `java.io.tmpdir` to a dedicated path under `/var/tmp/kafka` for Connect workers. On AL2023-style hosts, `/var/tmp` is often tmpfs — wiped on every reboot. Nothing in our packaging recreated that directory on boot. After patch night, Connect started cleanly; the failure only hit on the **first produce** with `compression.type=zstd`, when zstd-jni tried to unpack into a tmpdir that didn’t exist.

**The fix:** Create the directory with correct ownership, restart the Connect **process** (not just the task), and encode it in **tmpfiles.d** (and optionally `ExecStartPre`) so every worker survives the next reboot. Same unit pattern on siblings — this was a fleet ops gap, not a one-off corruption.

**Impact:** Source streaming was blocked for that shard until we restored the path; consumers lagged. A separate Telegraf/Jolokia vs Prometheus JMX port mismatch was monitoring noise only — useful reminder to align what we scrape with what the JVM actually exposes.

**Takeaway:** After reboot, `ls -ld /var/tmp/kafka` before you blame Kafka. zstd on Connect means natives in tmpdir — if the path isn’t there at **process** start, restarting the task alone won’t save you.

---

**Optional shorter version (if you prefer ~1 screen):**

Patch reboot → Kafka Connect task FAILED, broker healthy. Root cause: custom JVM tmpdir under tmpfs, never recreated on boot → zstd-jni couldn’t unpack natives on first send. mkdir + process restart + tmpfiles.d for the fleet. Pipeline back; lag cleared. Lesson: tmpdir hygiene is part of Connect ops, not an afterthought.

---

I kept internal host names, connector IDs, and account details out. If you want a specific tone (more “we” vs “I”, or emphasis on Ansible/fleet hardening), say which and I can tune a variant.