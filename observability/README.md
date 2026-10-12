# Observability

Everything needed to see FullSend the way an on-call engineer does.

| File | What it is |
|---|---|
| [`compose.yaml`](compose.yaml) | Local stack: the app, Prometheus and Grafana, bound to 127.0.0.1 |
| [`prometheus/prometheus.yml`](prometheus/prometheus.yml) | Scrape configuration |
| [`prometheus/rules.yml`](prometheus/rules.yml) | SLI recording rules and SLO burn-rate alerts |
| [`grafana/provisioning`](grafana/provisioning) | Data source and dashboard provisioning, loaded on start |
| [`grafana/dashboards/fullsend.json`](grafana/dashboards/fullsend.json) | The "FullSend · Service Overview" dashboard |
| [`SLO.md`](SLO.md) | The service level objective and error budget policy |
| [`RUNBOOK.md`](RUNBOOK.md) | What to do when each alert fires |
| [`POSTMORTEM_TEMPLATE.md`](POSTMORTEM_TEMPLATE.md) | Blameless postmortem template |

The lab that uses all of this is [Phase 6](../phases/06-reliability/README.md).
