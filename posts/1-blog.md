# When TLS 1.3-Only Broke Everything: An Akamai ↔ External LB Handshake Mismatch

## The incident

Requests to our backend nginx box stopped abruptly. Traffic from internal domains continued to flow normally, but every request routed through Akamai-hosted domains via the external load balancer (ELB) vanished before it reached nginx.

The blast radius was wide: multiple application frontends depended on that backend, so they all went down at once. From the outside, it looked like a backend outage. Internally, nginx was healthy and internal callers could still reach it.

That split — internal OK, external dead — was the first clue that the problem lived in the path *before* nginx, not in the application itself.

## Diagnosis

We started with the obvious checks from a frontend box: repeated `curl` requests against the affected endpoints.

The pattern was consistent: connections were being cut off **before** they reached our infrastructure. Akamai was terminating the handshake, not nginx or the app tier.

When we opened a ticket with Akamai, their initial read pointed at an **SSL/TLS certificate issue**. That was a reasonable guess, but it didn’t match reality — **no certificate or cert configuration had changed** recently.

We kept digging into what *had* changed. The mismatch turned out to be in **TLS security policy alignment** between two layers:

| Layer | TLS policy |
|-------|------------|
| External LB | `TLS 1.3` only |
| Akamai property | Akamai-supported (prefers **1.2 → 1.1 → 1.0**, not 1.3-only) |

Akamai’s “supported” policy negotiates downward through older TLS versions. The external LB was configured for **TLS 1.3 handshake only**. There was no overlap in acceptable negotiation behavior: Akamai could not complete a 1.3-only handshake the way the LB expected, the TLS handshake failed, and Akamai dropped the connection.

No nginx access logs spike. No app errors. Just silent failure at the edge — classic TLS policy drift.

### Why this is easy to miss

- **Symptoms look like an outage**, not a config change.
- **Certificates are the default suspect**; policy mismatches are quieter.
- **Internal traffic still works**, which can send you hunting in the wrong place (backend, nginx, app).
- **Akamai sits in front**, so failures show up as “Akamai cut us off” rather than a clear LB error in your own logs.

## The fix

We changed the external LB TLS security policy from **TLS 1.3 only** back to a policy that **supports both TLS 1.2 and TLS 1.3**.

Traffic resumed immediately. No nginx restart, no cert rotation, no Akamai property rebuild — just policy realignment.

### Operational checklist (what we do now)

When updating TLS policy on an external LB that sits behind Akamai:

1. **Check Akamai property TLS settings** before changing the LB (match negotiation behavior, not just “we want modern TLS”).
2. **Coordinate with Akamai** if the LB policy moves to 1.3-only or any non-default policy.
3. **Test from outside the VPC** — internal curls are necessary but not sufficient; they won’t exercise the Akamai → ELB path.
4. **Document the pairing**: ELB policy name ↔ Akamai property TLS mode, so the next change isn’t a surprise.

There’s no fancy automation in this story yet — the “automation” is really **process**: treat ELB TLS policy changes as a cross-team change that includes Akamai config review.

## Lessons learned

1. **TLS policy is a contract between hops.** Certificate validity isn’t enough; both sides must agree on protocol version and cipher negotiation.
2. **“TLS 1.3 only” is not universally safe at the edge.** Upstream CDNs and legacy integration paths often still expect 1.2 fallback behavior.
3. **Split-brain symptoms narrow the search.** Internal OK + external broken → look at CDN, WAF, and LB in that order, not the backend first.
4. **Vendor “cert issue” hints aren’t always wrong, but verify the delta.** Ask: *what changed in the last deploy/maintenance window?* Policy updates count.
5. **Communicate before you change edge TLS.** Any external LB TLS policy update should trigger an Akamai property review (and vice versa if Akamai TLS settings change).

## Takeaway

A one-line TLS policy change on the external load balancer — moving to TLS 1.3 only — was enough to break every Akamai-fronted frontend, even though nginx and certificates were untouched. The fix was restoring a **dual 1.2/1.3 policy** and establishing a rule: **edge TLS changes always get paired with Akamai configuration review.**

If you’ve seen “random” external outages while internal health checks stay green, add TLS policy parity to your runbook before you reissue a single certificate.

---

*Status: resolved. Remember: whenever the external LB TLS policy is updated, coordinate with Akamai for the corresponding property change.*

---

I can also produce a shorter “incident summary” version for Confluence/DocLogs, or add a mermaid sequence diagram of the failed vs successful handshake if you want that next.