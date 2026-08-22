**Phase 1 — LinkedIn draft (from your template)**

---

**Why your liveness probe can fail even when `/healthCheck` is “instant”**

We chased intermittent Kubernetes probe failures on a Java/Spring Boot service — readiness and liveness both hitting the same lightweight endpoint.

The symptoms looked scary:
- `context deadline exceeded`
- occasional `connection refused` during startup/shutdown
- failures clustered during HPA scale events and pod churn

The twist: when the health handler actually ran, logs showed **~0 ms** static 200 OK responses. It wasn’t checking Redis, DB, or anything downstream.

**Root cause:** thread-pool saturation, not a broken health check.

With a **1s probe timeout**, health requests shared Tomcat’s worker pool (~200 threads) with heavy API traffic. Under load, probes queued behind slow requests and never got headers back in time. Load-balancer health checks on the same path added more pressure. Cache/Redis errors showed up on business APIs — they slowed threads and made probe starvation worse, but they weren’t what `/healthCheck` was testing.

Fresh pods looked healthy because their pools were empty. Older pods recovered when load shifted. Classic load-dependent, intermittent behavior.

**Impact:** We avoided the wrong fix (blaming cache logic in the health endpoint) and focused on what actually helps:
- raise probe timeout
- separate liveness vs readiness (and LB checks) where possible
- fix upstream latency that eats thread pool headroom
- don’t treat “new pod is fine” as “problem solved”

**Lesson:** If your health endpoint is trivial but probes time out — check thread-pool exhaustion before you chase dependency connectivity.

Have you seen probe failures that *look* like dependency issues but turn out to be capacity?

#Kubernetes #DevOps #SpringBoot #SRE #PlatformEngineering

---

**Checkpoint:** This is a single post draft — impact, challenge, solution, human tone, no internal specifics.

Want a **shorter version** (~120 words), a **more technical** variant, or tweaks to tone (more story / less bullet-heavy)?