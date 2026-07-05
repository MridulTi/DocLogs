Here are a few LinkedIn-ready options based on your story. Pick the tone that fits you best.

---

### Option 1 — Short & punchy

**When traffic stops, the cause isn’t always where you look.**

We had a sudden outage: internal requests were fine, but traffic from our CDN stopped reaching the backend entirely. Multiple frontends went down with it.

After ruling out the app layer, we traced the failure to the CDN edge — not our nginx or backend. Their team pointed to TLS, but nothing on our cert side had changed.

The real issue? A mismatch in TLS security policies. Our external load balancer had been updated to **TLS 1.3 only**. The CDN was configured for broader compatibility (1.2 → 1.1 → 1.0). TLS 1.3-only expects a 1.3 handshake; the CDN couldn’t complete it, so connections were dropped before they ever hit our stack.

**Fix:** Align the LB policy to support both TLS 1.2 and 1.3. Traffic restored immediately.

**Lesson:** Infrastructure changes don’t live in isolation. Any TLS policy update on the origin side needs a coordinated check with your CDN team.

---

### Option 2 — Slightly more narrative

**A TLS policy change broke production — and it looked like a backend outage.**

Requests from internal domains kept flowing. Requests from our Akamai-hosted domains didn’t. Several application frontends that depended on one backend nginx box went dark at once.

We spent time on the wrong layer first — curls from the frontend, nginx checks, the usual suspects. The breakthrough came when we realized Akamai was cutting off the connection before it reached us. They flagged SSL, but our certificates hadn’t changed.

Root cause: our external LB TLS policy had been set to **TLS 1.3 only**, while Akamai was on a compatibility mode that negotiates down from 1.2. No overlap → failed handshake → silent drop.

Rolling the LB policy back to **TLS 1.2 + 1.3** fixed it on the spot.

**Takeaway for infra teams:** TLS policy updates on your load balancer aren’t a local change. Loop in your CDN partner before you flip the switch.

---

### Option 3 — One-liner hook + bullets (good for engagement)

**Internal traffic worked. CDN traffic didn’t. Same backend. Different TLS handshake.**

What happened:
- External LB TLS policy → TLS 1.3 only  
- CDN → compatibility mode (1.2 and below)  
- Handshake failed at the edge; requests never reached nginx  

What we learned:
- A “small” LB config change can take down every CDN-facing frontend  
- Always coordinate TLS policy changes with your CDN team  

Glad this one’s resolved — and documented for next time.

---

### Hashtag suggestions (optional, 3–5 max)

`#DevOps` `#SiteReliability` `#Infrastructure` `#IncidentResponse` `#TLS`

---

**Sanitization note:** These drafts avoid internal hostnames, domain names, and team-specific tooling. If you want a more personal voice, add one line like *“Spent a good hour convinced nginx was the problem…”* — that reads well on LinkedIn without exposing internals.

Want a version tailored to a specific audience (hiring managers, SRE peers, or leadership)? I can adjust tone and length.