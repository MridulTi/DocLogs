# When the Right SSH Key Still Couldn't Clone: Jenkins, Bitbucket, and SSH's "First Match Wins" Trap

The Jenkins job had been green for months. Then one morning it just… stopped. Same pipeline, same repo, same server — but the checkout stage hung until timeout. No fancy credential plugin, no stored secret rotation: SCM was set to **none**, so Git used whatever SSH identity the Jenkins user had on the box. That part had always been intentional. We wanted cloning to ride the service account's keys, not a Jenkins-managed credential object that might drift from what ops actually deployed.

I pulled the console log expecting the usual suspects — DNS, disk, Bitbucket maintenance. Instead I got a permission failure on a repo we'd been building forever. That mismatch — authentication seemed fine in isolation, authorization clearly wasn't — is what sent us down a rabbit hole that took longer than it should have.

## The setup

Our build agents share a dedicated Unix user. That user's `~/.ssh/config` points at Bitbucket with a handful of RSA keys listed — not one key per host alias, but several `IdentityFile` entries under the same `Host bitbucket.org` block. Historical reasons: different teams had appended keys over the years, some tied to old automation, some to personal Bitbucket accounts that got folded into org access patterns. We'd never had a reason to clean it up because "it worked."

The failing job was stuck on checkout of the main application repo. Other jobs on the same agent, other repos, other users on the same machine — we started comparing all of them because the failure didn't smell like Jenkins itself. Jenkins was just spawning `git fetch`; the pain was underneath, in SSH.

## What we tried first (and why it didn't help)

The obvious move: verify the keys. We picked three keys from the config that we *knew* worked — tested manually as the Jenkins user, `ssh -T git@bitbucket.org`, clone the repo by hand. All three succeeded in isolation. So the keys weren't expired, weren't wrong fingerprints, weren't missing from Bitbucket. That part was solid.

We diffed the Jenkins user's environment against another service account on the same host that could clone fine. Shell, `HOME`, `SSH_AUTH_SOCK` (empty in both cases — agent wasn't in play), config file layout, file permissions on `~/.ssh`. Nothing jumped out. Same Bitbucket host stanza shape, same `IdentitiesOnly`… actually we toggled that too, thinking maybe SSH was offering keys we didn't intend. Still stuck in the job.

We bounced the agent, cleared workspace, re-ran. Same hang, same effective "can't get this repo" behavior. Impact was straightforward: no checkout, no build artifact, deploy pipeline blocked on that repo. Not a flaky test — hard stop at SCM.

At this point the team was split. Half convinced it was Bitbucket project permissions ("someone revoked access"). Half convinced it was Jenkins plugin weirdness with `none` credentials. Both hypotheses were wrong, but they ate a day because they *almost* fit the symptoms.

## The breakthrough: one key vs. many

What cracked it wasn't a new log line. It was a controlled experiment we should have run on hour one.

Temporarily trim the SSH config down to **a single** `IdentityFile` — one of the three we'd already proven worked — and re-run the job. Checkout succeeded immediately. Add the keys back one at a time, re-run. Still fine with two. Put the **full** set back — failure returns.

So the bug wasn't "no valid key." It was "valid key, wrong one first."

That sent me back to read SSH client behavior with fresh eyes. When you offer multiple keys to `git@bitbucket.org`, the client tries them in config order (modulo agent and `IdentitiesOnly` nuances). Bitbucket's SSH endpoint accepts the connection if **any** offered public key belongs to **some** Bitbucket user. Authentication succeeds. Git then runs server-side and checks whether **that** user may read **this** repository. If the first key that authenticates belongs to User A, and the repo is only granted to User B's key further down the list, you don't get a clean "try next key" loop for repo access the way you might expect from a mental model of "fallback keys."

In our case: every key in the config was registered on Bitbucket — attached to *some* account. The **first** key in the file authenticated successfully against Bitbucket SSH. That account did not have read access to the application repo. SSH had no reason to try the later keys that *did* have access, because from the server's perspective the handshake already succeeded. Manual tests with one key worked because we were only ever offering the good one. The job failed because the full config offered the bad-first ordering every time.

Once we saw it, we felt dumb. It's the kind of issue that looks like credential rot from the outside and like ACL drift from the permissions side, but is actually **identity selection** — a layer neither monitoring nor Bitbucket's UI surfaces clearly when "SSH works" in a one-off terminal test.

## What we changed

We didn't need a Jenkins change. We needed an SSH identity policy.

We converged on two acceptable patterns and picked one:

**Option A — one key to rule them all:** Single `IdentityFile` for `bitbucket.org` on build agents, full stop. Every repo the agent must clone has to grant that key (or its backing account) access. This is what we shipped.

**Option B — many keys, but equivalent access:** If you truly need multiple keys in config, every key listed must belong to identities that all have access to every repo that agent will touch — ideally the same Bitbucket account or a group with uniform repo permissions. "Registered on Bitbucket" is not the same as "can read this repo."

Concretely, we removed the stale `IdentityFile` entries from the shared config, kept the one service identity our org uses for CI, and documented that appending keys to the agent SSH config requires a repo-permission audit, not just `ssh -T` succeeding.

We also added a cheap guardrail: a small script the Jenkins user can run in CI dry-run mode that attempts clone against a canary repo using the **full** config, not a manually narrowed test. Catches ordering regressions if someone merges another key "because it worked on their laptop."

Why it worked: shrinking the offered identity set removed the "first key auths but can't read" failure mode. Git over SSH stopped landing on the wrong Bitbucket user.

## What I'd do differently

I'd run the **single-key vs. full-config** experiment before comparing users across the server. The `-T` test and manual clone with one `-i` flag gave false confidence because they never reproduced the multi-key offer set the job actually used.

The lesson I keep repeating internally isn't "monitor SSH" or "communicate better." It's narrower and more annoying:

> For shared CI users, either expose **one** key to Bitbucket, or ensure **every** key in `~/.ssh/config` can access **every** repo that user will clone. SSH won't reliably skip a key that auths-but-lacks-repo-access and try the next one.

If your SCM credential is `none`, Jenkins isn't picking the key — your SSH config order is. Treat that config like production routing: one path, explicitly owned, or you're gambling on which Bitbucket user wins the handshake first.