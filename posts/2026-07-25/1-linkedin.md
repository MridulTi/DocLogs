Here’s a LinkedIn-ready post based on your template and sanitized notes:

---

**When the cron is running but the disk is still full**

This week we hit the same problem three times: a Logstash node at ~97% disk usage, even though our hourly S3 upload job was firing on schedule.

At first glance, it looked like a broken cron. It wasn’t.

The real issue was a broken **log lifecycle** — several layers stacked on top of each other:

**The ghost disk (~51 GB “invisible” to `du`)**  
The upload script had deleted active `.log` files while Logstash still had them open. `df` showed ~82 GB used; `du` showed ~31 GB. Classic deleted-but-open file leak. One restart released the inodes.

**Compressing logs Logstash was still writing**  
The script tried to zstd-stream active files. Size changed mid-read → upload failed → logs piled up locally.

**Logrotate vs upload mismatch**  
`copytruncate` created rotated copies (`.log.1`, dated files) that the upload script didn’t consistently pick up — while active logs kept growing.

**Volume + side effects**  
High ingest (~2+ MB/s on one app alone), file output writing everything to disk regardless of ES success, and mapping errors still landing on disk.

**The fix: separate rotate from archive**

- **Logrotate** owns rotation: `copytruncate`, no compress at rotate time, frequent runs for large files  
- **Upload script** never touches active `*.log` — only closed rotated copies, with an `lsof` check before upload  
- **One-time cleanup**: restart Logstash, force logrotate, run upload  

**Impact:** We stopped treating “disk full” as a cron failure and fixed the pipeline end-to-end. Clear monitoring signals now: `df` vs `du` gap → `lsof +L1`; failures in upload logs.

**Lesson learned:** Active `.log` = Logstash owns it. Only archive rotated snapshots. Compress after rotation, not during.

Three script iterations in one week taught us that patching one symptom isn’t enough when ingestion, rotation, upload, and process file handles are all coupled.

---

**Optional shorter version** (if you prefer brevity):

---

Our Logstash node hit 97% disk three times this week. Cron was fine — the log lifecycle wasn’t.

Deleted-but-open files (~51 GB ghost disk), zstd on active logs, and logrotate/upload mismatches meant each “fix” only patched one layer.

We separated concerns: logrotate rotates closed snapshots; upload only archives `.log.1` / dated files after an `lsof` check. Never touch active logs while Logstash is writing.

Result: repeatable runbook, no more false “cron is broken” incidents, and clear signals (`df` vs `du`, upload log failures) for next time.

Golden rule: **active `.log` = Logstash owns it.**

---

Want a more technical tone, a “lessons for SRE teams” angle, or a version that omits tool names (`lsof`, `zstd`) for a broader audience? I can adapt it.