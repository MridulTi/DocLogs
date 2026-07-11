# Jenkins couldn't clone our repo, and every SSH key we tested worked — until we used all of them at once

The build job had been sitting in the queue for twenty minutes when I finally opened the console log and saw the same line I'd been seeing all morning: `git fetch` hanging on authentication, then timing out. No failed credential message. No permission denied that pointed at a specific key. Just silence, then failure. We'd already verified the deploy key. We'd already confirmed the Jenkins service user could `git clone` the repo from an interactive shell — or at least, we thought we had. The job was still stuck, and we couldn't cut a build of the app repo.

## The setup nobody thinks about until it breaks

Our Jenkins jobs pull from Bitbucket over SSH. For this particular SCM configuration, credentials were set to **none**. That means Jenkins doesn't inject a stored credential; it relies on whatever SSH identity the OS user running the job has available. On our build server, that user has an `~/.ssh/config` with several `IdentityFile` entries — multiple RSA keys, three of which we'd used successfully on other projects and knew were valid Bitbucket keys.

The mental model most of us had was straightforward: SSH tries keys until one works. If any of those three keys can authenticate, cloning should succeed. We'd used that pattern for years across different repos and never had a reason to question it.

The impact was blunt. Without a successful clone, the pipeline never got past checkout. No artifact. No build. Jobs piled up behind the same failure. Not a flaky network blip — reproducible, annoying, and blocking release work.

## First pass: the obvious suspects

We started where you always start. Wrong key? We pulled the public halves from the three "known good" keys and checked them against Bitbucket — attached to accounts, not revoked, still listed. The repo's access controls looked fine for at least one of those keys when we tested in isolation.

Wrong user? Jenkins runs as a dedicated service account. We compared that account's SSH setup with other users on the same server who *could* clone without issue. File permissions on `~/.ssh` looked correct. `config` syntax looked fine. We diffed `authorized_keys` and agent setups — nothing jumped out as a smoking gun. Two users on the same machine, similar configs, different outcomes. That comparison should have been a clue, but at the time it mostly deepened the confusion.

We also sanity-checked the Jenkins side. SCM URL format, branch spec, clean workspace toggles — all normal. The failure wasn't a malformed remote URL; it was authentication stalling in a way that felt like SSH was *almost* working.

I remember the frustration of those tests because they all succeeded outside Jenkins. Log in as the Jenkins user, run `git clone git@bitbucket.org:our-org/our-app.git`, and sometimes it worked. Run it again, same user, same shell — worked again. That made us chase ghosts in Jenkins plugin config and job parameters for longer than I want to admit.

## Where it stopped making sense

The break in our mental model came when we deliberately narrowed the key set.

We edited the service user's `~/.ssh/config` down to a single `IdentityFile` — one of the three keys we'd already verified — and re-ran the clone from that user's shell. Clean success. Every time. Fast handshake, repo on disk, no drama.

Then we put the full config back. Multiple `IdentityFile` lines, the way the server had been set up for years because different teams had dropped their keys on a shared build host. Clone failed again. Same user. Same repo. Same Bitbucket. The only variable was how many keys SSH was willing to offer.

That experiment flipped the problem from "Jenkins can't authenticate" to "SSH is authenticating with the wrong identity and stopping."

## What SSH was actually doing

To understand why "more keys" made things worse, you have to sit with how the OpenSSH client behaves during publickey authentication — not how we wished it behaved.

When you connect to `git@bitbucket.org`, the client reads your configured identity files (and anything loaded in an agent) and offers public keys to the server **in order**. The server responds to each offer. For each key, Bitbucket can effectively say: "Yes, I recognize this key as belonging to *some* account" or "No, I don't know this key."

Here's the trap we walked into: **recognition is not authorization.**

Several of our keys were registered in Bitbucket — attached to real users, valid, not expired. The first key in our config was one of them. Bitbucket's SSH endpoint accepted the authentication at the key level. From SSH's perspective, the handshake for that key succeeded. So the client stopped trying additional keys.

But that first key's Bitbucket account did not have read access to *this* repo. Access control failed later in the Git layer, or the session ended up in a state where the clone couldn't proceed — depending on exactly how Bitbucket surfaces repo-level denial for a valid-but-unauthorized key. The symptom on our side was the same either way: hung or failed fetch, no clear "wrong key" error, because we hadn't offered the wrong key. We'd offered a *right key for the wrong scope*.

The keys further down the list *did* have access. We knew that because when they were first in the list — or the only key configured — cloning worked. SSH never reached them when the full config was loaded, because an earlier key had already "won" authentication.

This also explained the cross-user comparison that hadn't helped earlier. Another user on the server might have had only one key, or their key ordering put the repo-authorized key first. Same Bitbucket, same repo, different `~/.ssh/config` shape. Looked like a user permission problem until we controlled for identity file ordering and count.

I don't have the exact `ssh -vvv` transcript saved from that day, but when we ran verbose mode with the full config, the story was visible in the authentication dance: one key accepted, then nothing useful afterward. With a single key configured, the log was short and the clone completed.

## Dead ends we spent time on

Not everything we tried was wasted, but some paths were false leads.

We spent time wondering if Jenkins was stripping environment or running in a context without the service user's home directory. That can happen with certain agent setups and `HOME` overrides. We ruled it out by making the job execute a trivial shell step that printed `whoami`, `echo $HOME`, and listed `~/.ssh`. It was the right user, the right home, the right files on disk.

We also wondered if `ssh-agent` was involved — keys loaded in the agent presenting before config-file keys and changing order. On this host, agent state was inconsistent between interactive login and the Jenkins worker process. That merited checking, but the single-key versus multi-key experiment worked the same in non-agent scenarios. Agent noise wasn't the root cause; it might have made ordering harder to reason about, but the failure reproduced with only `IdentityFile` directives and no agent.

Another rabbit hole: "maybe Bitbucket rate-limits or bans after too many key attempts." Plausible on paper, less plausible once we saw one accepted key and no subsequent offers in verbose output. The server wasn't cycling through six keys and giving up. It was stopping early.

## The fix, and why it held

We had two durable ways out, and we picked the one that matched how we wanted to operate the host long term.

**Option A — one key per operational scope:** Consolidate so the Jenkins service user offers exactly one identity for Bitbucket, and that identity has access to every repo that user must clone. Stop accumulating per-team keys in a shared `ssh/config`.

**Option B — every offered key must be valid for every repo:** Keep multiple keys only if they are all guaranteed to authorize for all repos the host touches — same Bitbucket account, same project permissions, or deploy keys added repo-by-repo for each key you list. That gets unwieldy fast.

We went with Option A for the shared build user. Generate or designate a single deploy/service key, add it to Bitbucket with the right project access, trim `~/.ssh/config` to one `IdentityFile` for `bitbucket.org`, restart the stuck jobs. Checkouts succeeded immediately. No Jenkins credential object required because we'd fixed the underlying SSH identity selection — but we also documented that "credentials: none" means "whatever keys this user offers," and that's now a reviewed change surface.

Concretely, the config went from something shaped like this — illustrative, not a literal paste from the server:

```sshconfig
Host bitbucket.org
  HostName bitbucket.org
  User git
  IdentityFile ~/.ssh/team_a_deploy_rsa
  IdentityFile ~/.ssh/team_b_deploy_rsa
  IdentityFile ~/.ssh/legacy_ci_rsa
```

to:

```sshconfig
Host bitbucket.org
  HostName bitbucket.org
  User git
  IdentityFile ~/.ssh/ci_bitbucket_rsa
  IdentitiesOnly yes
```

`IdentitiesOnly yes` was belt-and-suspenders. It tells SSH not to wander off into agent keys or default paths and offer identities we didn't intend. On a shared CI user, explicitness beats convenience.

We did not delete the old keys from disk immediately. We removed them from the active config, confirmed pipelines for multiple repos, then rotated and archived according to our key hygiene process. The important part was **ordering and cardinality of offered keys**, not that the extra private keys were inherently corrupt.

## What I'd do differently next time

The lesson from this incident is specific, not a poster about communication or staging environments.

**SSH publickey success is per-key, early-exit, and unrelated to repo ACLs.** If the first offered key authenticates to the forge but lacks repository permission, you can have a pocket full of valid keys and still fail — and the failure won't look like "bad password." It'll look like CI is haunted.

**Shared build users compound the problem.** Every `IdentityFile` line you add is an ordering decision you probably never made consciously. Comparing "user A works, user B doesn't" without diffing the *ordered set of identities offered to that host* sends you chasing Jenkins bugs when the client did exactly what it was designed to do.

**"Credentials: none" is not "no credentials."** It delegates trust to the OS user's SSH setup. That's fine until the SSH setup is a museum of team keys. Treat `~/.ssh/config` on CI users as production config, version-reviewed, with as few identities as you can justify.

Next time I see a clone hang on a host with multiple keys, I'll run the single-key isolation test before I touch Jenkins. Ten minutes with a trimmed config would have saved us hours. I didn't capture exact queue times or latency numbers from the failed handshakes, but I remember the shape of the failure clearly enough: authentication that looked healthy and access that never arrived — because SSH had already committed to the wrong winning key.