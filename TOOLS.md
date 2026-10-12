# Tools and the policy behind them

## Policy

1. **Official or established stewardship.** Every tool comes from an official
   project, a foundation (CNCF and the wider Linux Foundation, the Python Software
   Foundation, PyPA) or a major vendor. Small one-person projects are not used, even
   when popular, because a learning path should not depend on one maintainer's spare time.
2. **Excluded origins.** Tools and AI services whose origin or owning company falls
   under this project's exclusion policy are not used or recommended, directly or
   indirectly. The deny-list in [`scripts/repo_audit.py`](scripts/repo_audit.py) is
   stored as SHA-256 hashes, so the repository never names those products, and CI
   fails if one appears in any file. Where a tool's origin could not be confirmed, it
   was left out.
3. **Official documentation first.** Commands and versions come from each tool's own
   documentation and release tags ([SOURCES.md](SOURCES.md), [VERSIONS.md](VERSIONS.md)).
4. **Pinned, then updated deliberately.** Exact versions everywhere; GitHub Actions by
   full commit SHA. Dependabot proposes updates; a human reviews them.
5. **No AI attribution.** Commits, pull requests and files carry the author's name
   only. The same audit rejects AI attribution markers in any file.
6. **Licences respected.** Tools are installed from their official sources under their
   own licences; nothing from them is copied into this repository.

## The tools

| Tool | Used for | Steward | Licence | Phase |
|---|---|---|---|---|
| Python | Everything you write here | Python Software Foundation | PSF License | 0 |
| pip, venv | Installing packages, isolating environments | PyPA / CPython | MIT / PSF | 0 |
| Git | Version control | Git project | GPL-2.0 | 0, 2 |
| FastAPI · Pydantic · Uvicorn | The practice app | FastAPI project · Pydantic · Uvicorn project | MIT · MIT · BSD-3-Clause | 0 |
| pytest · pytest-cov | Unit, API and tooling tests | pytest-dev | MIT | 2 |
| HTTPX | Test client and the triage agent's HTTP client | Encode | BSD-3-Clause | 2, 7 |
| Playwright for Python | Browser end-to-end tests | Microsoft | Apache-2.0 | QA track |
| Ruff | Linting and formatting | Astral | MIT | 2 |
| mypy | Strict type checking | Python (python/mypy) | MIT | 2 |
| PyYAML · jsonschema | File and Kubernetes schema validation | YAML project · python-jsonschema | MIT · MIT | 5 |
| Docker Engine / Docker Desktop | Containers | Docker Inc. | Engine: Apache-2.0; Desktop: Docker's subscription terms (free for personal use, education, non-commercial open source and small businesses) | 3 |
| Python Docker Official Image | Base image | Docker Official Images program | Image contents keep their own licences | 3 |
| Nginx | Reverse proxy and load-balancing lab | Nginx, Inc. | BSD-2-Clause | 1 |
| GitHub Actions, CodeQL, Dependabot, GHCR | CI/CD, code scanning, updates, image registry | GitHub | GitHub terms | 4 |
| Trivy | Image vulnerability scanning | Aqua Security | Apache-2.0 | 3, 4, 7 |
| Kubernetes, kubectl | Orchestration | CNCF | Apache-2.0 | 5 |
| kind | Local Kubernetes clusters in Docker | Kubernetes SIGs | Apache-2.0 | 5 |
| Helm | Packaging Kubernetes apps | CNCF | Apache-2.0 | 5 |
| Argo CD | GitOps delivery | CNCF project | Apache-2.0 | 5 |
| Terraform | Infrastructure as code | HashiCorp, an IBM company | BUSL-1.1 since Terraform 1.6 (production use allowed except competing hosted or embedded offerings; read the licence) | 5 |
| Terraform AWS provider | AWS resources | HashiCorp | MPL-2.0 | 5 |
| terraform-aws-modules (VPC, EKS) | Tested building blocks for the EKS lab | Community organisation on the Terraform Registry, widely used | Apache-2.0 | 5 |
| AWS CLI, Amazon EKS | The optional cloud lab | Amazon Web Services | Apache-2.0 (CLI); EKS is a paid service | 5 |
| Prometheus · prometheus-client | Metrics and alerting | CNCF | Apache-2.0 | 6 |
| Grafana | Dashboards | Grafana Labs | AGPL-3.0 | 6 |
| OpenTelemetry (Python) | Tracing | CNCF | Apache-2.0 | 6 |
| pip-audit | Dependency vulnerability audit | PyPA | Apache-2.0 | 7 |
| Bandit | Python security linting | PyCQA | Apache-2.0 | 7 |
| MCP Python SDK | The CI triage agent | Model Context Protocol (LF Projects) | MIT | 7 |
| Homebrew · WinGet · Python Install Manager | Installing tools on macOS and Windows | Homebrew project · Microsoft · Python Software Foundation | — | 0 |

Mentioned for further study but not installed here: OpenTofu (Linux Foundation),
HashiCorp Vault, Falco (CNCF), the OpenTelemetry Collector, Jaeger (CNCF).

## Using an AI assistant with this repository

Any assistant you choose is your decision; this repository does not depend on one.
Whatever you use, the rules in [Phase 2](phases/02-workflow/README.md#6-working-with-an-ai-assistant-honestly)
and [`ai-ops/GUARDRAILS.md`](ai-ops/GUARDRAILS.md) apply: verify every claim, never
paste secrets, keep writes behind a human, and keep AI credit lines out of commits.
