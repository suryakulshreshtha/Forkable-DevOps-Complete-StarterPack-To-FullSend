# FullSend runbook

Every alert in `prometheus/rules.yml` links to a section here. A good runbook entry
answers: what does this mean for users, how do I confirm it, and what do I try first?

Useful links while the lab stack runs: Prometheus alerts <http://127.0.0.1:9090/alerts>,
Grafana dashboard "FullSend · Service Overview" <http://127.0.0.1:3000>.

## FullSendErrorBudgetFastBurn

**Meaning for users:** a noticeable share of API calls are failing right now. At this
rate the 30-day error budget is gone in about two days or less.

**Confirm**

1. Grafana: is "Error ratio vs SLO threshold" above the budget line on both the 5m and 1h series?
2. Prometheus: `sum by (route, status) (rate(http_requests_total{route=~"/api/.*", status=~"5.."}[5m]))` shows which routes fail.
3. Logs: `docker compose -f observability/compose.yaml logs app --tail 50` (or `kubectl -n fullsend logs deploy/fullsend --tail 50`) and look for `"status": 503`.

**Mitigate first, investigate second**

1. Did a deploy just happen? Roll back: `kubectl -n fullsend rollout undo deploy/fullsend` (Kubernetes) or restart the previous image (Compose).
2. In this lab the usual cause is chaos injection: check `CHAOS_ERROR_RATE` in the ConfigMap or Compose environment and set it to `0`.
3. Post in the incident channel: what users see, what you are doing, when the next update comes.

**Afterwards:** write a postmortem with `POSTMORTEM_TEMPLATE.md` if the budget dropped below 50%.

## FullSendErrorBudgetSlowBurn

**Meaning for users:** a low but steady failure rate. Nothing is on fire, but at this
pace the budget runs out before the 30-day window does.

**Confirm:** compare the 6h and 3d error ratios in Prometheus
(`fullsend:api_error_ratio:rate6h`, `fullsend:api_error_ratio:rate3d`) and find the routes responsible with the query above.

**Act:** this is a ticket, not a page. Find the cause during working hours: a flaky
dependency, a slow memory leak causing restarts, or a release that raised errors slightly.

## FullSendDown

**Meaning for users:** possibly a full outage, or only that Prometheus cannot reach the app.

**Confirm**

1. Is the app up? `python scripts/smoke_test.py http://127.0.0.1:8000` (or through a port-forward on Kubernetes).
2. If the app answers, the problem is scraping: Prometheus → Status → Targets shows the error.
3. If it does not answer: `kubectl -n fullsend get pods` and `kubectl -n fullsend describe pod <name>` for crash loops, failed probes or image pull errors.

**Mitigate:** roll back the last change; if pods cannot be scheduled, check node capacity with `kubectl describe nodes`.

## FullSendSlowResponses

**Meaning for users:** the API works but is slow; 95th-percentile latency has been above 250 ms for 10 minutes.

**Confirm:** Grafana "Latency percentiles". Is p50 also up (everything is slow) or only p95/p99 (some requests are slow)?

**Common causes:** CPU saturation (check pod CPU against requests), too few replicas
for the load (`kubectl -n fullsend get hpa`), or a noisy neighbour on the node.

**Mitigate:** scale out (`kubectl -n fullsend scale deploy/fullsend --replicas=4`), then find the root cause.
