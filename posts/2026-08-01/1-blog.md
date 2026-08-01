# Eight Jenkins masters, one runbook, and the day AL2023 refused to behave like Amazon Linux 2

The alert wasn't a pager — it was a 404 during `dnf install jenkins` on the first clone target. We were mid-wave on a Jenkins master migration: eight production controllers, each moving from an old host onto a fresh Amazon Linux 2023 box running Jenkins 2.568.1 and Corretto 25. The source masters stayed live and read-only the entire time. All the scary work happened on targets only.

That 404 felt small. It wasn't. It was the first of several places where "we've done this before on AL2" quietly stopped being true.

## What we were actually doing

Our org runs a fleet of Jenkins masters — spread across accounts and teams. The upgrade goal was straightforward on paper: get everything onto Jenkins 2.568.1 with Java 25, on AL2023, without touching production controllers during the clone phase.

We started with a small account as the pilot, turned that into a written runbook (`Jenkins-Master-Clone-Runbook.plan.md`), then drove the same phased checklist through all eight hosts. Jira story tracked the parent work; each instance got its own sub-task and worklog. Calendar time for the full wave came in around one day plus six hours — not because any single host was fast, but because we stopped re-learning the same AL2023 surprises on every box.

The standard process per controller looked like this:

1. Inventory the source (read-only): Jenkins and Java versions, `JENKINS_HOME` size, users, listening processes, disk layout, nginx and other sidecars.
2. EBS snapshot of the source primary volume — no impact on the running master.
3. Create a volume from the snapshot; attach it as a secondary device on the **target only** (`/dev/xvdf` → nvme), mount read-only at `/mnt/jenkins-clone`.
4. On the target: install `jenkins-2.568.1` and `java-25-amazon-corretto`; stop and disable Jenkins before copying data; configure the JVM via a systemd drop-in.
5. Create OS users (`jenkins`, `ops`, `sec`, …); rsync `JENKINS_HOME`, home `.ssh` directories, and inventoried service configs (`/etc/nginx`, `/opt`, cron, systemd) from the clone mount.
6. Unmount and detach the secondary volume — but **keep** the snapshot and volume tagged for rollback. Do not delete them.
7. Enable and start Jenkins plus docker, nginx, and anything else we found in inventory; validate `:8080`, plugins, credentials, and agent nodes.
8. ELB/target group cutover stayed manual and separate — only after validation passed.

Safety gates were non-negotiable: never mutate source, snapshot before copy, retain rollback volumes, merge SSH keys instead of overwriting, validate before any load balancer attach. I used Cursor as the operator for inventory, AWS/SSM/SSH phases, and validation, while keeping cutover decisions and approvals in human hands.

## The first host teaches you everything (if you write it down)

### Dead GPG keys and a Java config that silently moved

The GPG failure was our entry point. The older runbook pointed at a Jenkins key URL that 404'd on AL2023. Package install couldn't proceed until we switched to `jenkins.io-2023.key` from `pkg.jenkins.io`. Easy fix once you know it; wasted time if you trust stale docs.

Then Java. On AL2 we'd leaned on `/etc/sysconfig/jenkins`. On AL2023 with Jenkins 2.568+, that file simply didn't drive the runtime anymore. Jenkins came up on whatever the system default was unless we told systemd explicitly. We added a drop-in at `jenkins.service.d/override.conf`:

```ini
[Service]
Environment="JENKINS_JAVA_CMD=/usr/lib/jvm/java-25-amazon-corretto/bin/java"
Environment="JAVA_OPTS=-Djava.io.tmpdir=/var/lib/jenkins/tmp ..."
```

That second line wasn't cosmetic. AL2023 mounts `/tmp` as tmpfs — roughly half of RAM. Jenkins and plugins do a lot of temp work. On at least one host we watched `/tmp` fill or fail mid-operation. Pointing `-Djava.io.tmpdir` at `/var/lib/jenkins/tmp` on persistent disk fixed installs, plugin extraction, and a whole class of "works on AL2, dies on AL2023" behavior.

We also learned to validate Java using the path in `JENKINS_JAVA_CMD` — Corretto 25 — not whatever `java -version` prints from the default alternatives setup. The target stack keeps extra JDKs (8, 11, 17) where jobs and agents need them; the controller JVM is explicitly 25.

### rsync exit 23 and the copy that never ends

Data copy is the long pole. `rsync -a` from the read-only clone mount hit SELinux xattr noise and returned exit code 23. If you treat rsync exit codes as gospel, you'll think you failed when you didn't. We switched to `rsync -a --no-xattrs` and verified by size and file presence instead of trusting the exit code alone.

one account had a `JENKINS_HOME` north of 13GB. That's hours, not minutes. We ran `nohup rsync` on the target and walked away. Later, after initial clones finished, we delta-synced builds that had landed on source during the first copy window — a follow-up pass worth scheduling explicitly so nobody assumes "rsync completed once" means "data is current."

Ownership drift was the next surprise after copy. AL2 → AL2023 rsync left UID and permission mismatches. Jenkins wouldn't behave correctly until we ran `chown -R jenkins:jenkins` on `/var/lib/jenkins` and aligned `/home/*/.ssh` modes and owners to match source. Jobs that use SSH agents fail in boring, repetitive ways when `.ssh` perms are wrong — we saw that on on account first and then checked the pattern everywhere else.

### The lockout on big account jenkins

This one got my attention.

While merging `authorized_keys` onto the new EKS-jenkins target , we overwrote instead of merged. SSH locked us out. Source of truth for "don't do that again" is now in the runbook in bold mental ink: **merge keys, keep `target.bak`, never blind overwrite.**

Recovery was SSM — break-glass access we had kept available on purpose. After that incident, every target stayed on SSH with SSM as backup. Some sources didn't even have SSH anymore; inventory and snapshot work went through SSM only on those hosts.

### git-client, /tmp, and Permission denied

On `fsm-eks`, Jenkins came up, plugins looked fine, credentials were there — and SCM checkouts broke with:

```
Permission denied on /tmp jenkins-gitclient-ssh*.sh-copy
```

The git-client plugin writes temporary SSH helper scripts under `/tmp`. Between tmpfs size limits, permission quirks, and the tmpdir override not yet applied everywhere, those scripts weren't executable when jobs needed them. Fixing execute permissions on the temp scripts **and** rolling the `java.io.tmpdir` pattern to other targets cleared the same failure mode before it bit every EKS-adjacent master.

### Sidecars you forget until jobs fail differently

Jenkins isn't just `:8080`. Inventory caught nginx, `/opt` tooling, cron, and systemd units on some hosts — easy to miss on the first pass if you're staring at `JENKINS_HOME` size and Java version. We added a Phase 2 process map and, when needed, re-attached the clone volume if we'd already detached the secondary EBS volume. Detach is correct for rollback hygiene; "oops we forgot nginx" is correct for operator humility.

## What actually changed (and why it held)

By the end of the wave, each controller had the same target footprint: AL2023 AMI, Jenkins 2.568.1-1, Corretto 25 as the controller JVM, with legacy JDKs retained where builds require them.

The mechanical fix sequence that repeated across hosts:

- Snapshot source → attach clone volume on target only → install RPM layout on empty target **before** overlaying `JENKINS_HOME` (so paths and packages exist, then data lands on top).
- Systemd drop-in for Java 25 and persistent tmpdir.
- rsync with `--no-xattrs`, then ownership and `.ssh` alignment.
- Merge `authorized_keys`; validate `:8080`, plugins, credentials, nodes.
- Leave snapshot + detached clone volume in place until cutover is solid.
- LB/TG: add target without removing source until traffic is verified — that step stayed with operators after Phase 7, not inside the automated clone runbook.

Cursor helped keep the work controlled rather than fast-and-loose. The agent ran AWS SSO, EC2 snapshot and volume attach, SSH/SSM inventory, install, rsync, and validate steps against the same checklist every time. We parallelized safe work — inventory and snapshots across accounts — while serializing risky steps: SSH key merge, Jenkins start, validation. Lessons from early hosts (GPG URL, tmpfs, authorized_keys, git-client) went back into the plan before the next clone. That's why eight masters in ~1d 6h beat a multi-week manual slog where each team rediscovers the same AL2023 footguns.

Post-first-wave follow-ups were predictable once the pattern was visible: delta sync for late-arriving builds, permission alignment on remaining targets, and the git-client SSH helper fix rolled to any host showing the same `/tmp` script errors.

## What I'd carry forward

This wasn't a single-root-cause outage story. It was eight near-misses compressed into one upgrade wave — and the interesting part is how many failures were **configuration contract changes** between AL2 and AL2023, not Jenkins itself. Sysconfig Java gone. tmpfs `/tmp`. New GPG key path. rsync xattrs. Each one is small alone; together they'll eat a week if you don't capture them after host one.

The practices that actually saved us:

- **Read-only source, write-only target** — no heroics on production boxes.
- **Rollback artifacts kept on purpose** — snapshot plus detached clone volume until cutover is boring.
- **A runbook that gets edited mid-flight** — the clone wasn't the finish line; it was the template.
- **SSM as break-glass** — not theoretical after .
- **Validate before the load balancer** — `:8080` and plugins aren't enough if git checkouts and SSH agents are broken.

If I did it again, I'd bake the delta rsync and `.ssh` ownership checks into the standard Phase 7 checklist instead of treating them as follow-ups. I'd also flag large `JENKINS_HOME` hosts upfront in the Jira sub-tasks so nobody schedules cutover conversations before the nohup rsync finishes.

Eight controllers. One consistent 2.568.1 / Java 25 footprint. No source mutations during clone. parent Jira closed with sub-tasks and time logged per host. The upgrade wasn't dramatic once the runbook caught up to AL2023's reality — which, honestly, is the best kind of production work.
