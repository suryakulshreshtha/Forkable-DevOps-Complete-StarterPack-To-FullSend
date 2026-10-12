# Phase 6 · Reliability: SLOs, observability, incidents

**Time:** 2–3 weeks · **Roadmap map:** milanm/DevOps-Roadmap step 10 (monitoring and observability)

**You finish with:** a dashboard and alerts built on an SLO, an incident you caused,
handled from the runbook, written up as a blameless postmortem, and an honest
view of where AI helps on call.

## Why hiring teams care

- Google SRE postings describe engineering "SLOs, monitoring, rollout safety, and production safety systems".
- NVIDIA's senior SRE posting asks for "SLO/SLI build, incident command" and its DevOps posting for moving monitoring "from reactive to proactive using AI-powered observability tools" for root-cause analysis and anomaly detection.

---

## 1. Concepts that make on-call bearable

| Term | Meaning |
|---|---|
| Monitoring vs observability | Monitoring answers known questions ("is it up?"); observability lets you ask new ones of metrics, logs and traces without shipping new code |
| Metrics · logs · traces | Numbers over time (cheap, aggregatable) · events with detail · one request's path through services |
| Four golden signals | Latency, traffic, errors, saturation: the Google SRE book's starting set for any user-facing system |
| SLI | A measured ratio, e.g. good requests ÷ all requests |
| SLO | The target for an SLI over a window, e.g. 99% over 30 days ([`observability/SLO.md`](../../observability/SLO.md)) |
| SLA | A contract with penalties; always looser than the internal SLO |
| Error budget | 1 − SLO. Spending it on releases and experiments is fine; running out means slowing down |
| Burn rate | How fast the budget is being used; 1 = exactly on budget for the window |
| Multiwindow, multi-burn-rate alerts | Page only when a long **and** a short window both burn fast: few false alarms, fast detection, quick reset |

## 2. What FullSend already exposes

| Signal | Where |
|---|---|
| Traffic, errors | `http_requests_total{method, route, status}`, labelled by route **template** to keep the number of series small |
| Latency | `http_request_duration_seconds` histogram, buckets from 5 ms to 5 s |
| Business events | `fullsend_deployments_recorded_total{environment, status}` |
| Build info | `fullsend_build_info{version, git_sha, environment}` = 1 |
| Saturation | Process CPU and memory from the client library's default collectors |
| Logs | One JSON object per line, each with a `request_id` that the response echoes in `x-request-id` |
| Traces | OpenTelemetry, off by default: `OTEL_ENABLED=true` (with the `observability` extra installed) |

## 3. Lab A: the stack, the dashboard, the maths

Docker Desktop must be running. Ports bind to 127.0.0.1 only.

| Step | Command (same on every OS) |
|---|---|
| Start app + Prometheus + Grafana | `docker compose -f observability/compose.yaml up --build -d` |
| Generate traffic for two minutes | `python phases/06-reliability/load_gen.py http://127.0.0.1:8000 --seconds 120` |
| Grafana (anonymous viewer) | <http://127.0.0.1:3000> → Dashboards → FullSend → "FullSend · Service Overview" |
| Prometheus | <http://127.0.0.1:9090> → try the queries below |
| Check the budget maths | `python phases/06-reliability/slo_calc.py --slo 99 --window 30` |

Queries to type into Prometheus:

| Question | PromQL |
|---|---|
| Requests per second by route | `sum by (route) (rate(http_requests_total{route=~"/api/.*"}[5m]))` |
| Error ratio, last 5 minutes | `fullsend:api_error_ratio:rate5m` |
| p95 latency | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))` |
| Which build is running | `fullsend_build_info` |

## 4. Lab B: cause an incident on purpose

| Step | macOS / Linux | Windows PowerShell |
|---|---|---|
| Restart the app with 20% injected failures | `CHAOS_ERROR_RATE=0.2 docker compose -f observability/compose.yaml up -d app` | `$env:CHAOS_ERROR_RATE="0.2"; docker compose -f observability/compose.yaml up -d app` |
| Keep traffic flowing | `python phases/06-reliability/load_gen.py http://127.0.0.1:8000 --seconds 300` | same |
| Watch the alert go pending → firing | <http://127.0.0.1:9090/alerts> | same |

Then run the incident like a team would:

1. **Declare it.** Write one line: what users see, when it started, who leads.
2. **Follow the runbook** for `FullSendErrorBudgetFastBurn` in [`observability/RUNBOOK.md`](../../observability/RUNBOOK.md). Mitigate before you investigate.
3. **Mitigate:** set the chaos rate back to `0` and restart the `app` service.
4. **Measure the damage:** how much budget did you spend? Use Grafana's burn-rate tile and `slo_calc.py --errors <n> --requests <n>`.
5. **Write the postmortem** with [`POSTMORTEM_TEMPLATE.md`](../../observability/POSTMORTEM_TEMPLATE.md). Blameless: "the config allowed a 20% failure injection in production" beats "Sam set the variable".

Incident roles from the Google SRE book's "Managing Incidents" chapter, scaled down for a team of one to three:

| Role | Does |
|---|---|
| Incident commander | Owns the incident, assigns work, decides; does not debug |
| Operations lead | The hands on the keyboard |
| Communications lead | Regular updates to stakeholders, so engineers are not interrupted |

## 5. Lab C: traces

| Step | macOS / Linux | Windows PowerShell |
|---|---|---|
| Install the extra (already done by `tasks.py setup`) | `python -m pip install -e ".[observability]"` | same |
| Run with tracing to the console | `OTEL_ENABLED=true python -m fullsend` | `$env:OTEL_ENABLED="true"; python -m fullsend` |
| Make a request and read the span printed in the terminal | `curl -s http://127.0.0.1:8000/api/v1/info` | `curl.exe -s http://127.0.0.1:8000/api/v1/info` |

To send spans to a real backend, set `OTEL_EXPORTER_OTLP_ENDPOINT` to an OTLP/HTTP
endpoint; the exporter reads it on its own (`src/fullsend/observability.py`).

## 6. AI on call: where it helps, where it bites

Observability vendors now ship AI "SRE agents" that triage incidents. New Relic
launched one in February 2026 and reported, from its own customers' data, 25%
faster incident resolution for users of its AI capabilities. That is a vendor's
figure, not an independent study. Keep two ideas apart:

| | AI watching your systems (AIOps) | You watching your AI (LLM observability) |
|---|---|---|
| What | Anomaly detection, alert correlation, suggested root causes | Latency, cost, errors and quality of the AI features you run |
| Risk | Confident wrong root causes; acting on stale or partial data | Silent quality drops that no 5xx ever shows |
| Guardrail | Ground it in real telemetry, keep a human approving every action, measure its false positives | Treat model calls like any dependency: SLIs, budgets, alerts |

Phase 7 builds a small, read-only AI triage tool and shows those guardrails in code.

## The Python tools in this phase

| Script | What it does |
|---|---|
| [`slo_calc.py`](slo_calc.py) | Error budget, downtime allowance, workbook alert thresholds, burn rate from observed errors |
| [`load_gen.py`](load_gen.py) | Mixed read/write traffic with status counts and p95 |

## Check yourself

```text
python -m pytest phases/06-reliability
```

The checks prove the maths reproduces the SRE Workbook's table, that the alert rules
use those thresholds, that every alert links to a runbook section that exists, and
that the load generator sees injected failures against a real running server.

## Interview questions

1. Define SLI, SLO and SLA for an API you know. Who sets each?
2. Why alert on burn rate instead of "error rate above 1% for 5 minutes"?
3. Your SLO is 99.9% over 30 days. How many minutes of total outage is that?
4. What are the four golden signals, and which one is hardest to measure well?
5. You are paged at 3 a.m. What are your first three actions?
6. What makes a postmortem blameless, and why does it matter for reliability?
7. Why label metrics by route template and not by the full URL?
8. An AI agent suggests a root cause with high confidence. How do you decide whether to act on it?

## AI exercise (with guardrails)

After Lab B, give an assistant **only** your timeline and the PromQL results (no
hostnames, no secrets) and ask it to draft the postmortem summary and three action
items. Then edit it: is any claim unsupported by your data? Are the action items
prevent / detect / mitigate, with owners? Log what you kept and what you changed.

## Done when

- [ ] You read the dashboard during load and can explain every panel
- [ ] You caused, mitigated and wrote up an incident using the runbook and template
- [ ] You can do burn-rate maths on a whiteboard
- [ ] `python -m pytest phases/06-reliability` passes

## Official docs

- Google SRE book, Monitoring Distributed Systems (golden signals): <https://sre.google/sre-book/monitoring-distributed-systems/>
- Google SRE book, Managing Incidents: <https://sre.google/sre-book/managing-incidents/>
- Google SRE book, Postmortem Culture: <https://sre.google/sre-book/postmortem-culture/>
- Google SRE Workbook, Alerting on SLOs: <https://sre.google/workbook/alerting-on-slos/>
- Prometheus recording and alerting rules: <https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/> · <https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/>
- Prometheus histograms: <https://prometheus.io/docs/practices/histograms/>
- Prometheus Python client (ASGI): <https://prometheus.github.io/client_python/exporting/http/asgi/>
- Grafana provisioning: <https://grafana.com/docs/grafana/latest/administration/provisioning/>
- OpenTelemetry Python: <https://opentelemetry.io/docs/languages/python/>
- New Relic SRE Agent announcement (vendor): <https://newrelic.com/press-release/20260224>

Previous: [Phase 5](../05-kubernetes-iac-cloud/README.md) · Next: [Phase 7 · Security and AI](../07-security-ai/README.md)
