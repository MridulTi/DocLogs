# Jenkins couldn't clone our repo — and the SSH key was fine

The job had been sitting in "checkout" for twenty minutes. No error banner, no obvious credential failure — just a hung SCM step while Jenkins tried to clone the app repo. We'd seen flaky network before, but this one kept reproducing on the same agent, same branch, same everything.

## The setup nobody questions until it breaks

Our Jenkins job was configured with SCM credentials set to **none**. That means clone auth comes from whatever SSH identity the job user has on the agent — not a stored Jenkins credential. On that box we had an `ssh_config` with several RSA keys listed. Three of them we'd used successfully elsewhere. The key itself wasn't the mystery; when we forced a single key, clone worked.

We compared the job user against other users on the server. Same OS, same Jenkins agent, same rough SSH layout. Nothing jumped out. That part was genuinely frustrating — it looked like a user-level misconfiguration, but the diff never materialized.

## SSH succeeded too early

The breakthrough wasn't "wrong key." It was **too many keys that all looked valid**.

Every key in our config was registered to *some* Bitbucket account. SSH would walk the list, pick the first one Bitbucket accepted, and stop. Authentication succeeded. From SSH's point of view, the handshake was done.

But Bitbucket auth and repo access aren't the same thing. The first matching key might belong to an account that can log into Bitbucket but **doesn't have permission on this repository**. SSH never falls through to the next key — it already got a successful auth response — so clone hangs or fails in a way that doesn't scream "permissions."

When we trimmed the config down to a single key — one we knew had access to that repo — the job unstuck immediately. Same server, same user, same Jenkins job. The only change was how many identities we offered.

That explained why one-key worked and many-keys didn't, and why comparing users across the server didn't help: the failure mode depends on key order and which Bitbucket accounts those keys map to, not on anything obvious in `/etc/passwd`.

## What we changed

We picked one of two sane policies and stuck to it:

1. **One key for SCM** — the job user's `ssh_config` should expose a single identity for Bitbucket, and that key must have access to every repo that user needs to clone.

2. **Or, every key in the config must be equivalent** — if you keep multiple keys, each one needs repo access (or they all need to live under the same Bitbucket account with the right permissions). Otherwise the first match wins and the rest never get tried.

We went with option one for the Jenkins job user. Less surface area, and the failure mode is easier to reason about next time.

## The thing I'll actually remember

"SSH works" and "I can clone this repo" are different questions. With multiple keys, SSH stops at the first account Bitbucket recognizes — even if that account can't see your project.

If you run Jenkins with `none` credentials and lean on the agent user's keys, audit the whole chain: what's in `ssh_config`, what order keys are tried, and whether **every** key that might win the race can actually reach **every** repo that job touches. We lost a morning to a key that was correct for Bitbucket and wrong for the repository.