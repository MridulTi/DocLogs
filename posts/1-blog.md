# Jenkins couldn't clone our repo — until we counted the SSH keys

The build job had been sitting in "checkout" for twenty minutes. No error banner, no obvious credential failure in Jenkins — just a hung SCM step and a repo that wouldn't come down. We'd seen this pattern before when keys were wrong or missing, but this time the keys were *right*. At least, three of them were.

## The setup that looked fine

One of our Jenkins jobs talks to Bitbucket over SSH with SCM credentials set to **none**. That means Jenkins doesn't inject a stored credential; it uses whatever SSH identity the job's OS user picks up — typically from `~/.ssh/config` and the keys sitting next to it.

That user had several RSA keys configured. We'd verified three of them against Bitbucket and they worked when tested manually. Clone from my laptop, clone as a different user on the same server, compare `~/.ssh` layouts — nothing obvious jumped out. Same host, same repo URL, same kind of config. The job user just couldn't get a clean checkout.

Impact was straightforward: the pipeline never got past source control, so we couldn't produce a build of the app repo at all.

## Chasing ghosts

We burned time on the usual suspects. Wrong key? Didn't look like it — we'd already proven multiple keys were valid. Permissions on `~/.ssh`? File ownership? Jenkins user vs. deploy user? We lined up configs side by side with other accounts on the box and still couldn't spot a meaningful difference.

The break came when we simplified the experiment: run the clone with **one** key in play. It worked. Add the full set of keys back into `ssh_config` and it failed again.

That narrowed it from "Jenkins is broken" to "something about having *multiple* identities available."

## What SSH was actually doing

OpenSSH doesn't round-robin keys until one can read your repo. It walks the configured identities in order. For each key, it asks the server: does this authenticate?

All of our keys were registered in Bitbucket — but under different users, and not every user had access to **this** repository. The first key in the list successfully authenticated to Bitbucket's SSH endpoint. From SSH's point of view, that was success. It never moved on to the next key.

So we had a failure mode that *looked* like a permissions or credential problem but was really an **identity ordering** problem: auth succeeded, authorization for the repo did not, and the client had no reason to try the key that actually had access.

Once we saw that, the stuck job made sense. Jenkins wasn't hanging on a bad password; it was stuck behind an SSH handshake that had already committed to the wrong identity.

## What we changed

We didn't need a clever Jenkins plugin fix. We needed SSH to present the right key — or for every key we expose to be able to do the job.

Concretely, that means one of:

- **One key** for the Jenkins user across the repos it needs to touch, or
- **Every key** listed in `ssh_config` must have access to every repo that user clones, or
- All those keys belong to the **same Bitbucket account** that owns the access you expect

We trimmed the config so the job user only offered the identity that actually had rights to the app repo. After that, checkout finished in seconds and builds started moving again.

If you're on a shared CI host with a fat `~/.ssh/config`, it's worth a quick audit: list the `IdentityFile` entries in order and ask, for each one, "if SSH stops here, can this key clone *every* repo this user needs?" The first match wins. Bitbucket won't ask for a second key just because the first one can't read your project.

## What I'd do differently next time

When SCM creds are `none`, the debugging surface isn't Jenkins — it's the OS user's SSH identity stack. I'd test with `GIT_SSH_COMMAND="ssh -v"` early and watch which key gets offered first, instead of assuming "key works in isolation" implies "key works in production config."

And I'd treat "multiple valid Bitbucket keys on one machine" as a smell, not a convenience. They can all authenticate. They can't all authorize. SSH won't sort that out for you.