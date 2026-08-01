**LinkedIn post (ready to paste)**

---

Just wrapped upgrading **8 production Jenkins controllers** to **2.568.1 on Amazon Linux 2023 with Java 25** — without touching the live masters during the work.

**The challenge:** Move each controller to a new host, keep config/jobs/credentials intact, and avoid downtime risk on systems teams still depend on daily. Large homes, OS differences (AL2 → AL2023), and “small” gotchas (tmpfs `/tmp`, systemd Java config, SSH keys) can turn one upgrade into a long, fragile weekend.

**What we did:** Built a repeatable runbook: snapshot the source volume → attach read-only on the target → install Jenkins/Java on the new box → rsync data and sidecars → validate before any load-balancer cutover. Sources stayed read-only the whole time; rollback volumes stayed until we were confident.

**Impact:**
- **8/8 controllers** on a consistent, supported stack
- **~1 day + 6 hours** end-to-end for the full wave (vs. a multi-week manual slog)
- A reusable pattern for the next round of controller upgrades

**Lessons worth sharing:**
- On AL2023, don’t assume old Jenkins install notes still work — GPG keys and Java config paths change
- Point Jenkins temp dir off tmpfs — large plugin/job work will fill `/tmp` fast
- Merge `authorized_keys`, don’t overwrite (SSM saved us once)
- Fold fixes from host #1 back into the runbook before host #2 — that’s what made the pace safe *and* fast

Grateful for good runbooks, explicit safety gates, and tooling that helps execute them consistently while a human stays in the loop for the decisions that matter.

---

**Optional shorter version (~900 chars)**

Upgraded **8 Jenkins production controllers** to **2.568.1 + Java 25 on AL2023** using a clone-and-cutover pattern: snapshot source → read-only attach on target → rsync → validate → manual LB switch. Live sources were never mutated.

Finished the full wave in **~1 day 6 hours** with a reusable runbook. Big wins: consistent stack, clear rollback, lessons from early hosts applied to the rest (tmpfs `/tmp`, systemd Java overrides, SSH key merges).

Repeatable infra upgrades aren’t about speed alone — they’re about making safety boring.

---

**What I left out (on purpose):** private IPs, internal hostnames, Jira keys, and account-specific details. Say if you want a version that names **Jenkins/AL2023/Cursor** differently or leans more “leadership” vs “hands-on engineer.”