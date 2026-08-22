# Why our liveness probe timed out even though `/healthCheck` never touched Redis

The alert looked like a dependency outage. Readiness and liveness on our Java service were failing in bursts — `context deadline exceeded (Client.Timeout exceeded while awaiting headers)` — and around the same window, application logs were full of cache and Redis errors. My first instinct was to trace the health handler and ask whether we'd accidentally started pinging Redis on every probe.

We hadn't. The handler was a static 200 OK. When it actually ran, it logged ~0 ms. That mismatch — probes dying while the health code looked fine — is what sent us down the wrong path for a few hours, and what eventually made the real cause obvious.

## What we were running

The service is a Spring Boot app behind an ingress and an AWS target group. Kubernetes runs liveness and readiness as HTTP GETs against the same path: `/healthCheck`. Period 10 seconds, `timeoutSeconds: 1`. The load balancer runs its own health check on the same path and port every 10 seconds.

That endpoint is deliberately dumb. It does not call Redis, a database, or anything downstream. Passing the probe only proves the HTTP server can accept a request and return a response. We treat dependency health elsewhere; this path is supposed to be cheap.

Under normal traffic, that design works. During an HPA scale event, it did not.

## When things started failing

Failures weren't steady. They clustered when the deployment scaled or pods churned — new replicas coming up, old ones draining, traffic shifting. Fresh pods looked fine. Older ones in the middle of the fleet would fail probes, then sometimes recover after load redistributed. Less often we saw `connection refused` on pods that were starting or terminating; that part felt like noise until we separated it from the timeout failures.

The timeout failures were the scary ones. Kubernetes marked pods not ready or restarted them. From outside, it looked like the service was unhealthy. From inside, when we grepped logs for the health handler itself, we kept finding fast 200s — but only on the requests that actually reached the handler.

That distinction mattered. We weren't looking at a slow health check. We were looking at health checks that sometimes never got a thread in time.

## Chasing Redis (and missing the point)

The timeline overlap with Redis/cache errors made this harder than it should have been. Business API paths were logging codec and connectivity issues. Latency on those endpoints spiked. It was reasonable to wonder if `/healthCheck` had grown a dependency check we didn't know about, or if Spring's health aggregation had been turned on for something we thought was isolated.

We walked the handler and confirmed: static response, no downstream calls. Optional jar/source review would have been redundant — runtime logs already showed 0 ms when the handler executed. So the cache errors were real, but they weren't *in* the probe path. They were on API traffic that shared infrastructure with the probe path.

That was our first dead end as a root cause, though not as a contributing factor. Fixing Redis wouldn't fix probe timeouts by making `/healthCheck` faster — there was nothing left to speed up in the handler itself. But Redis slowness could still make everything worse if it blocked the threads that were supposed to serve probes.

## Thread pool saturation

Tomcat serves `/healthCheck` and every API route from the same worker thread pool. We had the pool capped around 200 threads. Under load, especially during scale events when traffic hadn't yet spread evenly, worker threads filled up with slow API work. Redis trouble on those paths added latency and kept threads busy longer.

Probes don't wait politely. Kubelet hits liveness and readiness every 10 seconds with a 1-second timeout. The target group adds another `/healthCheck` every 10 seconds per instance. Those requests land in the same queue as everything else. If all 200 threads are tied up waiting on cache calls or slow downstream logic, a probe sits in the accept queue until the client gives up waiting for headers.

Hence the error text: not a connection failure to Redis, not a 500 from the health handler — `Client.Timeout exceeded while awaiting headers`. The TCP connection might succeed; the response never starts in time.

Once we framed it that way, the intermittent pattern made sense. New pods after scale-up had empty pools and a smaller share of traffic until the service settled. They passed probes immediately. Older pods holding more connections and hotter thread utilization failed first. Pods we terminated showed `connection refused` because the process was already gone — expected, and a different failure mode from starvation.

We didn't capture exact queue depths or a precise latency number in the notes from that shift. What we had was correlation: HPA events, probe failures, high thread occupancy, and cache errors on API paths — not on the health handler when it ran.

## Why "raise the timeout" wasn't the whole story

Raising `timeoutSeconds` above 1 would give probes more time to wait for a free thread. That's a valid mitigation and probably stops the bleeding on liveness kills. But it treats the symptom. A 3-second probe timeout on a handler that executes in 0 ms is a signal that something else is wrong with capacity or isolation.

We weighed a few changes together:

**Increase probe timeout.** Low risk, quick to deploy. Buys headroom when the pool is briefly saturated. Doesn't fix API slowness or reduce thread contention.

**Separate probe traffic from application traffic.** A dedicated connector or a minimal probe path served on a different thread pool (or even a sidecar/admin port) means kubelet and the load balancer aren't competing with `/api/...` for the same 200 workers. This is more work but addresses the architectural coupling.

**Fix the cache codec errors on API paths.** Indirect but real. Errors that slow business requests keep threads pinned longer, which increases the odds that a probe waits past 1 second. The health endpoint wasn't broken; the pool was over-subscribed because of problems elsewhere.

**Stop triple-stacking the same path.** Liveness, readiness, and the target group all hammer `/healthCheck` on the same port. Each alone is light; combined with API load on one pool, they're another source of contention. Readiness might warrant a slightly richer check; liveness should stay as dumb as possible — but not necessarily on the same threads as heavy traffic.

We didn't treat "make `/healthCheck` ping Redis so failures are honest" as a fix. That would have made probes fail for the wrong reason and conflated "app process up" with "cache reachable," which is exactly what we'd almost done when we misread the Redis log correlation.

## What actually changed

The immediate config change was increasing probe `timeoutSeconds` so transient saturation during scale events didn't restart pods. In parallel — because the evidence pointed at thread occupancy, not handler logic — we prioritized the cache errors on API routes that were holding threads and traced whether Tomcat's max threads and accept queue were appropriate for peak + probe overhead.

Longer term, the design direction was clear: isolate probe handling from the main servlet traffic, and avoid using one static endpoint for liveness, readiness, and external health checks without explicit headroom in the pool.

After deploy, the pattern we watched for was the same one that fooled us initially: new pods staying green while the fleet scales. That's not proof the problem is gone. It only means those instances haven't hit saturation yet. Validation was watching older replicas through the next HPA event and confirming probes stayed green while API latency and thread utilization stayed within bounds — and that when cache errors appeared, they didn't precede another wave of probe timeouts.

## What I'd check first next time

If the health handler is trivial and logs show 0 ms when it runs, but Kubernetes reports probe timeouts, I wouldn't start with dependency connectivity. I'd look at thread pool utilization, probe timeout vs period, and who else hits that path — kubelet twice (liveness + readiness), plus the load balancer — on the same connector as production API traffic.

Probe timeout is not the same as dependency failure. A 1-second timeout on a 0 ms handler is telling you the request didn't get served in time, not that the handler logic failed. `connection refused` on shutting-down pods is a separate signal from `awaiting headers` on live ones.

The lesson from this incident isn't "monitor more." It's narrower: **a healthy `/healthCheck` implementation can still fail probes when the HTTP server is saturated**, and log lines about Redis on other endpoints can send you on a long detour if you assume every failure mode must flow through the health handler itself.