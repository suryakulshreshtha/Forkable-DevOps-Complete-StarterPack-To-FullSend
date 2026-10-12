# FullSend service level objective

| Item | Value |
|---|---|
| Service | FullSend API (`/api/*` routes) |
| SLI (what we measure) | Share of `/api/*` requests that do **not** return a 5xx status, from `http_requests_total` |
| SLO (the target) | **99%** over a rolling 30 days |
| Error budget | 1% of requests, about 432 minutes of full downtime in 30 days |
| Excluded | Health checks and `/metrics` (they are not user traffic), 4xx responses (caller errors) |
| Alerting | Multiwindow, multi-burn-rate rules from the Google SRE Workbook, in `prometheus/rules.yml` |
| Owner | You (in this lab) |

## Why 99% and not 99.99%?

A lab service on a laptop, a kind cluster and a two-node EKS cluster cannot honestly
promise four nines; a single node restart would spend the whole month's budget.
Pick an SLO your users need and your system can meet, then raise it when both change.

## Error budget policy

| Budget left this window | What the team does |
|---|---|
| More than 50% | Ship normally. Spend budget on experiments and faster releases. |
| 10–50% | Every release needs a rollback plan; prioritise the top reliability issue. |
| Under 10% | Freeze feature releases; only reliability fixes and security patches ship. |
| Exhausted | Postmortem for what spent it; the freeze lasts until the burn rate is back under 1. |

Check the numbers any time: `python phases/06-reliability/slo_calc.py --slo 99 --window 30`.
