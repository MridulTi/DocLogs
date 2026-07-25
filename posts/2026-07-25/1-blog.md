# The cron was fine — our log lifecycle was eating 51 GB of ghost disk

The third pager this week landed at 2:47 AM with the same subject line: root filesystem on `devopsdevops-devops-v1-8-77` at 97%. I'd already verified the hourly S3 upload cron twice. `sudo crontab -l` showed the job firing at `:30` every hour. `sudo tail /var/log/pod-s3-upload.log` had entries — not silence, not permission errors, just the steady rhythm of a script that was supposedly doing its job. That mismatch is what kept me awake. The disk was lying about something, or the cleanup pipeline was lying about success.

## What this box actually does

This server is the central Logstash node for  EKS pod logs. Filebeat ships container logs to Kafka; Logstash consumes them and writes to two sinks: Elasticsearch for search, and local files under `/var/log/pod-logs-for-s3/{app}/{app}-YYYY-MM-dd-logstash-8-77.log` for archival. An hourly cron runs `pod_logs_upload_to_s3.sh`, which zstd-compresses those files and pushes them to `s3://-eks-prod-app-logs/containers-logs-prod/`. Logrotate config lives at `/etc/logrotate.d/eks-app-logs`. The Logstash file output config is in `/etc/logstash/conf.d/logs-output-to-files.conf`.

On paper it's a straightforward pipeline: ingest, rotate, upload, delete. In practice we'd patched three different things across three incidents and the disk kept filling anyway. That pattern usually means you're fixing symptoms at each layer without seeing the whole stack.

## The first wrong turn: "cron is broken"

My opening move was the obvious one. `df -h /` confirmed the pain — 85G volume, ~3G free, 96–97% utilization. Then `du -sh /var/log/pod-logs-for-s3/*/` to see which app directories were hogging space.

The numbers didn't add up.

`df` reported roughly 82G used on root. `du -shx /` came back around 31G. Fifty-plus gigabytes of disk usage with no corresponding directory footprint is a specific smell. I'd seen it before on log-heavy hosts, but I wanted proof before telling anyone we'd been deleting files that weren't actually gone.

```bash
sudo lsof +L1 | grep pod-logs-for-s3
```

There it was. Deleted inodes still held open by Logstash's Java PID, and they were still growing:

- `-app` — ~22 GB
- `-app` — ~12 GB  
- `` — ~7 GB

The upload script had successfully deleted active `.log` files while Logstash still had them open. From the filesystem's perspective those bytes were gone — `du` couldn't see them. From the kernel's perspective they were very much allocated until the process released the file descriptors. Classic ghost disk.

One-time relief was blunt but correct: `systemctl restart logstash` to release the inodes. That bought breathing room. It also told us we'd been treating "delete after upload" as safe on files Logstash was actively writing. It isn't.

So the cron wasn't broken. Part of our cleanup had been making the problem invisible to `du` while `df` kept climbing. That was incident one. We restarted Logstash, patted ourselves on the back, and moved on.

## Layer two: zstd screaming at files that wouldn't sit still

The ghost disk fix didn't stick. Within days the upload log started showing a different failure mode. The script was trying to `zstd`-stream files Logstash was still appending to. You can't compress a moving target cleanly — the read finishes and the file has grown:

```
zstd error 27: Incomplete read
```

Upload failed. Files stayed local. Disk kept growing.

There was another logic trap in the same script. It skipped today's and yesterday's files unless they were already >= 2048MB. On a node where `-app` alone was ingesting around 2.2 MB/s — roughly 190 GB/day of potential write volume if everything landed on disk — "wait until it's big enough" meant logs accumulated all day and then failed when we finally tried to touch them. `-app` at ~772 KB/s and `` at ~619 KB/s weren't as dramatic individually, but they compounded the same pattern.

We were compressing the wrong files at the wrong time. Active `.log` files belong to Logstash. The upload script had no business opening them.

## Layer three: logrotate and upload speaking different languages

While digging into rotation, I pulled the logrotate config:

```bash
sudo cat /etc/logrotate.d/eks-app-logs
```

It was using `copytruncate` with `compress`, `maxsize 500M`, `rotate 3`. That creates rotated copies — `.log.1`, date-stamped `.log-YYYYMMDD`, sometimes `.zst` — while truncating the active file in place so Logstash keeps writing to the same path.

Reasonable pattern. Except our upload script didn't consistently pick up `.log.1` and the other rotated artifacts. I found roughly 1.4 GB of rotated orphans sitting locally, never uploaded, while the active logs under the same app directories kept growing. Logrotate was doing its job-ish. The upload script was looking for a different shape of "done" file.

We had two independent systems both trying to manage lifecycle — rotate with compression in logrotate, compress-and-upload in the cron script — and neither owned a clear handoff point.

## Layer four: the firehose we weren't accounting for

Even with lifecycle bugs fixed, the volume math was ugly. Logstash's file output writes every event to disk regardless of whether Elasticsearch accepts it. ES was rejecting 39k+ events on `-app` indices — `mapper_parsing_exception` on a marker field — but those events still hit the local pod-log files. Disk pressure wasn't purely an archival bug; it was ingest volume meeting a pipeline that always persists locally.

That's a separate fix (mapping correction on the ES side). I mention it because it explained why "reasonable" rotation thresholds still felt tight. This node wasn't archiving a trickle. It was a central drain for multiple high-throughput apps.

## The flock that cried wolf

One more annoyance during the week: the upload script reported "Another instance is already running" when nothing was stuck. Turned out we had an external `flock` wrapper *and* an internal flock inside `pod_logs_upload_to_s3.sh`. Double-locking. False positives during overlapping cron windows or slow runs. We stripped the external wrapper and kept internal flock only.

Small thing, but it burned investigation time when I was already questioning whether cron was firing at all.

## What we actually changed

After three iterations that each fixed one layer, we stopped patching symptoms and separated concerns explicitly: **logrotate owns rotation; the upload script owns archival of closed files only.**

**Logrotate** (`/etc/logrotate.d/eks-app-logs`):

- `daily` + `maxsize 2048M` — aligned with the upload script's size threshold so we're not fighting different cutoffs
- `copytruncate` — Logstash keeps the same file path; no reload dance
- `nocompress` — rotation produces plain rotated files; compression happens once, at upload time
- `rotate 14` — enough local retention if an upload hour fails

Because `maxsize` triggers on size rather than just the calendar, logrotate needs to run frequently. We moved it to hourly at `:05`.

**Upload script** (`pod_logs_upload_to_s3.sh`):

- **Never** touch active `*.log` files — Logstash owns those until rotation
- **Only** upload rotated `*.log.1` / `*.log-YYYYMMDD` snapshots
- `lsof` check before upload — if something still has the file open, skip it
- zstd stream straight to S3; delete local copy only on successful upload
- Cron at `:35` — after logrotate at `:05`, giving rotated files time to exist and settle
- Internal flock only; no external wrapper

One-time cleanup on the box: restart Logstash (release ghost inodes), `logrotate -f` to normalize state, manual run of the upload script to drain backlog.

The mechanism that makes this work is boring on purpose. Logstash appends to `app-YYYY-MM-dd-logstash-8-77.log`. At `:05`, logrotate copy-truncates when size or daily threshold hits, leaving `app-....log.1` as a closed snapshot. At `:35`, the upload script compresses that closed snapshot, pushes to S3, deletes local. Logstash never loses its file handle. We never delete a path the JVM still thinks it owns.

## What I'd watch differently now

The monitoring insight that would have shortened this week: **`df` vs `du` gap means go straight to `lsof +L1`**, not another cron audit. And **`FAILED` lines in `/var/log/pod-s3-upload.log`** are lifecycle failures, not upload infrastructure failures.

The golden rule we wrote down for ourselves: active `.log` = Logstash owns it. Only upload `.log.1` rotated snapshots. Never delete a `.log` while Logstash is running — if you need emergency cleanup, restart first so the kernel can actually reclaim the inodes. `copytruncate` + `nocompress` in logrotate; compress once in the upload script after rotation.

We closed the disk runaway. The ES marker mapping on `-app` indices is still driving rejected-event volume onto disk — that's the next fire. But at least now when the pager fires, I won't spend the first hour proving cron works. I'll check whether something is trying to compress a file that's still moving.
