# Phase 8 · Capstone: your own FullSend, end to end

**Time:** 3–4 weeks · **Roadmap map:** all twelve milanm/DevOps-Roadmap steps plus the DevSecOps bonus, in one project

**You finish with:** a public repository that proves, with working code, what
Platform, SRE and DevOps postings ask for. One 2026 hiring guide we read calls a
public artifact that proves the outcome you own "the single strongest hiring
signal"; treat that as one blog's opinion, but it costs you nothing to have one.

---

## The brief

Build and operate a small service of your own (not FullSend) through the whole
loop. Pick something you care about: a URL shortener, a status page, a feature-flag
service, a webhook relay. Keep the app small; the platform around it is the point.

| Area | Must have | Stretch |
|---|---|---|
| App | Python; health endpoints; JSON logs; Prometheus metrics; config from env vars | A real database (PostgreSQL) with migrations |
| Tests | Unit + API tests, ≥ 85% coverage; Playwright tests for any UI | Contract tests for an API you call; load test in CI |
| Containers | Multi-stage, non-root, health-checked image; `image_audit.py` passes | Signed image with build provenance |
| CI/CD | Lint, type check, tests, security scans, image build/scan/push; every action pinned by SHA; least-privilege tokens | Preview environments per pull request |
| Kubernetes | Deployment with all three probes, PDB, NetworkPolicy, `restricted` Pod Security; Helm chart with a values schema | HPA with Metrics Server; canary with a progressive-delivery tool |
| GitOps | Argo CD syncs your chart from Git | Two environments promoted by pull request |
| IaC | Terraform for the cluster or for any cloud resource you use; plan guarded by `tf_plan_guard.py` in CI | Remote state with locking; policy checks on the plan |
| Reliability | A written SLO; burn-rate alerts; a dashboard; a runbook entry per alert | A chaos experiment with a hypothesis, run and written up |
| Incident | One induced incident, handled and written as a blameless postmortem | A game day with a friend as incident commander |
| Security | Secret scanning before commit; dependency and image scanning; threat table like Phase 7's | OIDC deploys from CI with no stored cloud keys |
| AI | AI log with honest entries; one AI-assisted tool with written guardrails and tests for them | An MCP server for your own service's operations |
| Docs | README with an architecture diagram, a quick start for macOS and Windows, and "what I would do next" | A 3-minute screen recording of a deploy and a rollback |

## Rubric (score yourself, then ask someone else to)

| Score | Meaning |
|---|---|
| 0 | Missing |
| 1 | Present, but you could not explain every line in an interview |
| 2 | Works, tested, and you can explain the trade-offs |
| 3 | Works, tested, explained, **and** you broke it on purpose and showed it recovers |

Aim for at least 2 in every row. A 3 in reliability, security or CI/CD makes a better interview story than another feature.

## Map to what postings ask for

| Hiring signal (from the postings in [SOURCES.md](../../SOURCES.md#hiring-signals)) | Your evidence |
|---|---|
| Kubernetes in production: probes, autoscaling, RBAC, network policy | Your chart, your manifests, your broken-then-fixed rollout |
| Terraform: modules, state, review | Your Terraform, your plan guard, your remote state |
| CI/CD as a product | Your pipeline file and how fast it runs |
| SLOs, monitoring, incident command | Your SLO doc, alerts, dashboard, postmortem |
| Python for automation | Every script in your repo, with tests |
| Daily, verifiable use of AI tools | Your AI log and your guarded AI tool |
| Security mindset | Your threat table and the controls that answer it |

## Write-up template for your README

```markdown
## What this is
One paragraph. Who would use it and why.

## Architecture
Diagram (draw it yourself) and one sentence per component.

## How it is built, tested and shipped
The pipeline, in order, with the reason for each stage.

## How I know it is healthy
SLO, alerts, dashboard screenshot, link to the runbook.

## An incident I caused on purpose
Link to the postmortem. What I learned.

## Trade-offs I made
Three decisions and what I gave up for each.

## What I would do next
Three items, in priority order.
```

## Before you call it done

- [ ] A stranger can clone it and follow your quick start on macOS **and** Windows
- [ ] CI is green, and main is protected by a ruleset
- [ ] `terraform destroy` has been run for anything that costs money
- [ ] No secrets anywhere in history (run your secret scan over the whole repo)
- [ ] Every commit is yours, in your words

Previous: [Phase 7](../07-security-ai/README.md) · Back to the [roadmap](../../README.md#roadmap)
