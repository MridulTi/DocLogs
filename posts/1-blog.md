# When TLS 1.3-only broke everything behind Akamai

The alert wasn't subtle. Requests just stopped hitting our backend nginx box. Internal traffic from our own domains kept flowing, but anything coming in through Akamai-hosted domains — routed via the External LB — went dead. Several frontends all depended on that backend, so they went down together.

We run nginx in front of a shared backend that multiple application frontends talk to. Under normal conditions, Akamai terminates at the edge, traffic crosses the External LB, and nginx forwards to the app tier. Internal paths bypass that edge path entirely, which is why the split behavior was our first real clue: the nginx box wasn't universally broken. Something in the Akamai → External LB path was failing.

## Chasing the wrong certificate

We started from the frontend boxes and ran curls against the backend path. The failures looked like they were getting cut off at Akamai — not nginx, not the app. That pointed outward, not inward.

We opened a ticket with Akamai. Their read was an SSL certificate problem. That didn't sit right. We hadn't rotated certs, renewed anything, or touched the cert chain on our side. If nothing on the certificate had changed, why would Akamai suddenly start rejecting handshakes?

We kept digging anyway. The Akamai angle was real — requests really were dying at their edge — but "certificate issue" felt like a symptom label, not the mechanism.

## The policy mismatch

While we were going back and forth, someone pulled up the External LB TLS security policy. That was the turn.

The LB had been set to **TLS 1.3 only**. At Akamai, the property was on their default supported policy — the one that negotiates down through **1.2 → 1.1 → 1.0**, not a strict 1.3-only handshake.

TLS 1.3-only on the load balancer means the server side of the handshake insists on 1.3. Akamai's side, configured for broader compatibility, wasn't going to meet it there. The handshake never completed. From the outside it looked like Akamai was cutting requests off — and in a sense it was, because the TLS negotiation failed before anything useful got through. Easy to misread as "SSL cert broken" when the real failure mode is protocol policy mismatch.

We hadn't changed certificates. We had changed (or inherited) a TLS policy that didn't match what Akamai could speak on that property.

## What fixed it

We rolled the External LB TLS security policy back to one that supports **both TLS 1.2 and TLS 1.3**. After that change, traffic from Akamai-hosted domains started reaching nginx again, and the dependent frontends came back.

No nginx reload drama, no cert redeploy — just aligning the LB's minimum/maximum protocol behavior with what the Akamai property actually negotiates.

## What I'm keeping in my head

The split between internal (working) and Akamai (broken) saved us from burning time on nginx config. But "Akamai says certificate" plus "we didn't touch certs" should have pushed us to TLS policy sooner.

The operational bit I care about: **any time we change TLS policy on the External LB, we need to coordinate with whoever owns the Akamai property config.** Edge and origin have to agree on what handshake they're willing to do. A 1.3-only LB in front of an Akamai property still on broad compatibility isn't a subtle drift — it's a hard cutoff.

I'm marking this one complete, but the runbook note is the part that matters for the next person: check LB TLS policy against Akamai's supported cipher/protocol set *before* you assume the cert is bad.