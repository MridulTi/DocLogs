# One Helm template change broke every Argo app — fixing nil `ingressInt` safely

The Slack thread started the way these things usually do: three people pasting the same Argo CD error within a few minutes of each other. Sync failed. Not one app — several. All on the same shared EKS platform, all pulling from the same application Helm chart we'd been using for ages.

I opened Argo first on the app I knew had deployed recently, then on two others that hadn't changed in weeks. Same failure. That ruled out my first instinct — a bad image tag or a typo in one team's values file. Whatever broke was upstream of individual app config.

## A shared chart, a feature merge, and a new template

Our platform pattern is familiar if you've run Kubernetes at any scale: dozens of services, one common chart, per-app and per-env values overlays. Argo CD watches the repo and syncs each Application to its cluster. Most apps define `ingress` for their primary routing. A subset also define `ingressExt` for a public-facing ALB. Nobody had needed an internal-only ingress type until recently.

A feature PR had landed that added support for internal ALBs — `ingressInt` — plus matching templates `ingress-int.yaml` and `ingress-ext.yaml` in the shared chart. The author needed internal ingress for one service, so they added an `ingressInt` block to that app's values file and merged. CI was green. The chart rendered fine in whatever path the PR exercised.

Then Argo tried to sync everyone else.

## Narrowing it down

Argo's UI isn't always generous with Helm errors, but the sync logs usually cough up the render failure. The message we kept seeing was the Helm classic:

```
Error: template: .../ingress-int.yaml:...: executing "..." at <.Values.ingressInt.enabled>: nil pointer evaluating interface {}.enabled
```

That line tells you almost everything. The template touched `.Values.ingressInt.enabled`. For the app that got the new values block, `ingressInt` exists and has an `enabled` field. For every other consumer of the chart, `ingressInt` was never defined. In Go-template land, `.Values.ingressInt` is `nil`, and dereferencing `.enabled` on nil is a hard stop — Helm never gets as far as creating or updating resources.

I pulled the diff from the feature merge. Two new template files, and at the top of `ingress-int.yaml`:

```yaml
{{- if .Values.ingressInt.enabled -}}
```

No default in the chart's root `values.yaml`. No guard checking whether `ingressInt` exists before reading `.enabled`. The template runs for every app on every `helm template` / `helm upgrade` — the `if` only skips the *body* of the template; the condition itself still evaluates `.Values.ingressInt.enabled` first.

That matched the blast radius. Apps with the new key: fine. Apps with only `ingress` and maybe `ingressExt`: broken. Apps that hadn't been touched in months: broken. Argo doesn't isolate chart render failures per consumer when they share a chart version — one bad optional key poisons the whole sync surface.

We briefly wondered whether we should patch values files app by app. There are a lot of them — dev, staging, prod overlays, team forks. Adding `ingressInt: { enabled: false }` everywhere would work, but it's the kind of churn that hides in a giant PR and still leaves you one missing file away from the next outage. The regression had already been introduced by adding `ingressInt` to a single app's values while the template assumed every app would have the key. Repeating that pattern at scale felt wrong.

## The fix: chart defaults and nil-safe guards

We wanted a chart-only fix — no hunting through dozens of per-env values files, no coordination with every team to add a stub block. Two changes, applied together.

**First**, add defaults in the chart's `values.yaml` so `ingressInt` and `ingressExt` always exist, even when an app never mentions them:

```yaml
ingressInt:
  enabled: false
  hosts: []
  annotations: {}
  tls: []

ingressExt:
  enabled: false
  hosts: []
  annotations: {}
  tls: []
```

Apps that need internal or external ALBs keep overriding these in their own values. Everyone else inherits disabled defaults and never thinks about the keys again.

**Second**, harden the templates so a missing or partial values merge can't take down render again. The condition in `ingress-int.yaml` became:

```yaml
{{- if and .Values.ingressInt .Values.ingressInt.enabled -}}
```

Same pattern in `ingress-ext.yaml` for consistency — same class of bug, same class of fix. The `and` short-circuits: if `ingressInt` is nil or absent after a bad merge, the template skips cleanly instead of panicking.

We reverted the one-off `ingressInt` block from the single app's values file. With chart defaults in place, that app could set `ingressInt.enabled: true` and its hosts/annotations when they actually needed internal ingress, without carrying a special snowflake block that implied the key was app-local rather than chart-wide.

After merging the chart fix, Argo syncs recovered across the board without touching individual Application manifests or env-specific values. The app that originally needed internal ingress still opts in through overrides; the rest of the fleet never knew anything happened except that sync went red and then green again.

## Why this works (and what we'd do differently)

Helm merges values layers: chart defaults, then parent charts, then user-supplied `-f` files and `--set`. If the chart doesn't define a key, and no values file defines it either, `.Values.ingressInt` is nil in the template context. Optional features can't assume every consumer opted in — especially on a shared chart where most apps will never use the feature.

Defaults alone would probably have fixed this specific incident, because `ingressInt.enabled` would resolve to `false` everywhere. We kept the nil guard anyway. Defaults can be overridden away, subcharts can omit keys, and someone will eventually add a third ingress variant the same way. The guard costs one line and buys immunity to the exact error we saw.

The process miss was visible in the PR itself: the feature was validated on one app that had `ingressInt` in values, while the template executed for all apps on the chart. A render check that only runs `helm template` with the happy-path values file wouldn't catch it. Next time, for optional blocks on a shared chart, I'd want CI to render against a minimal values fixture — just enough to deploy a generic app, with no `ingressInt` — alongside the feature app's overlay. If minimal render passes, you've got both defaults and guards covered, or at least you'll see the nil pointer before merge.

One template change broke every Argo app on the platform. Fixing it took chart-level defaults and a nil-safe condition, not a values-file scavenger hunt across the org. That's the pattern I'd reuse: when you add optional `.Values` blocks to a shared Helm chart, ship chart defaults *and* nil-safe template guards — not every consumer will define the key, and Argo will sync all of them on the same chart version whether you planned for that or not.