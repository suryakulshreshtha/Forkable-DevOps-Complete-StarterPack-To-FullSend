# Versions

Every version below was the latest stable release on **2026-10-12**, read from the
project's own release tags (`git ls-remote`), PyPI, or its official download page.
Where this pack deliberately uses something older, the reason is given.
Dependabot ([`.github/dependabot.yml`](.github/dependabot.yml)) proposes updates weekly
for Python packages, GitHub Actions, the Docker base image and Terraform providers.

## Languages and runtimes

| Item | Version used | Notes |
|---|---|---|
| Python | **3.14** (3.14.8) | Recommended. Docker base image `python:3.14-slim-trixie`; Homebrew `python@3.14` is 3.14.8. |
| Python | 3.15.0 (released 2026-10-09) | Tested in CI as a canary that may fail. Not the default: on 2026-10-12 PyYAML had no 3.15 wheels on PyPI, and the Docker Official Image library still listed 3.15 as a release candidate. |
| Python | 3.13 | Also tested in CI (security-fix status until 2029). |

## Python packages (pinned in [`pyproject.toml`](pyproject.toml))

| Package | Version | Extra |
|---|---|---|
| fastapi | 0.143.0 | app |
| uvicorn | 0.54.0 | app |
| prometheus-client | 0.26.0 | app |
| pytest · pytest-cov | 9.1.1 · 7.1.0 | dev |
| httpx | 0.28.1 | dev |
| httpx2 | 2.13.1 | dev (the Starlette test client uses it; without it the client warns, and warnings are errors here) |
| ruff · mypy | 0.17.0 · 2.4.0 | dev |
| pyyaml · jsonschema | 6.0.3 · 4.26.0 | dev |
| playwright · pytest-playwright | 1.63.0 · 0.10.0 | e2e |
| opentelemetry-api · -sdk · -exporter-otlp-proto-http | 1.45.1 | observability |
| opentelemetry-instrumentation-fastapi | 0.66b1 | observability (the contrib instrumentations are published as beta versions) |
| pip-audit · bandit | 2.10.1 · 1.9.4 | security |
| mcp (MCP Python SDK) | 2.3.0 | agent |

## GitHub Actions (pinned to full commit SHAs)

| Action | Version | Commit |
|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| actions/setup-python | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| actions/upload-artifact | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` |
| actions/dependency-review-action | v5.0.0 | `a1d282b36b6f3519aa1f3fc636f609c47dddb294` |
| docker/setup-buildx-action | v4.4.1 | `f87e5991a6d7451dcb8d9637bfbc97413f497069` |
| docker/metadata-action | v6.2.0 | `dc802804100637a589fabce1cb79ff13a1411302` |
| docker/build-push-action | v7.4.0 | `c3c9e263c25d99ce0380d002d59b67737d91b0dc` |
| docker/login-action | v4.6.0 | `dbcb813823bdd20940b903addbd779551569679f` |
| aquasecurity/trivy-action | v0.36.0 | `ed142fd0673e97e23eac54620cfb913e5ce36c25` (released after the March 2026 incident; pins `setup-trivy` v0.2.6 by hash) |
| github/codeql-action | v4.38.3 | `24c54180a607b1449ed407dd24f251e4e9147c8d` |
| hashicorp/setup-terraform | v4.0.1 | `dfe3c3f87815947d99a8997f908cb6525fc44e9e` |
| azure/setup-helm | v5.0.1 | `9bc31f4ebc9c6b171d7bfbaa5d006ae7abdb4310` |
| helm/kind-action | v1.15.1 | `1544676c07bb3570fcb70166beaa07c4528fd4aa` |
| aws-actions/configure-aws-credentials (Phase 4 example) | v6.3.0 | `e1253824e5c10ff9df46874f81ed3ec929e19cfd` |

Each SHA was checked against the tag in the action's own repository before release.

## Containers, Kubernetes and infrastructure

| Tool | Version used | Where |
|---|---|---|
| Trivy (binary used by the action) | v0.75.0 | `ci.yml` |
| Kubernetes API schema for validation | v1.37.1 | `scripts/validate_k8s.py` |
| kind | v0.33.0 | `infra.yml`, Phase 5 |
| kind node image | `kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5` | `infra/kind/kind-config.yaml` (kind v0.33.0's default, pinned by digest as its release notes advise) |
| kubectl | 1.37 | Phase 5 (keep within one minor version of your cluster) |
| Helm | v4.3.0 | `infra.yml`, Phase 5 (chart `apiVersion: v2`, which Helm 4 still supports) |
| Terraform | 1.16.5 | `infra.yml`; `required_version >= 1.10` for S3 native locking |
| AWS provider | `~> 6.68` (6.68.0) | `infra/terraform/aws-eks/versions.tf` |
| terraform-aws-modules/eks | 21.29.0 | `main.tf` (needs AWS provider ≥ 6.59) |
| terraform-aws-modules/vpc | 6.7.3 | `main.tf` |
| Amazon EKS Kubernetes version | 1.37 | Newest on EKS, standard support since 2026-10-01 |
| Argo CD | stable manifest (v3.5.5 on 2026-10-12) | Phase 5, official install command |
| Nginx (Phase 1 lab) | 1.30.5 | `phases/01-foundations/nginx-lab/compose.yaml` (the Docker Official Image's `stable` line; mainline was 1.31.6) |
| Prometheus | v3.15.0 | `observability/compose.yaml` |
| Grafana | 13.2.3 | `observability/compose.yaml` (`grafana/grafana`, the repository Grafana now recommends) |
| Dev container image | `mcr.microsoft.com/devcontainers/python:3.14` | `.devcontainer/devcontainer.json` |
| Dev container features | docker-in-docker 4 · kubectl-helm-minikube 1 · terraform 1 | `.devcontainer/devcontainer.json` |

## Mentioned in lessons, not installed by this repository

| Tool | Latest on 2026-10-12 |
|---|---|
| OpenTofu | v1.13.1 |
| HashiCorp Vault | v2.1.2 |
| Falco | 0.45.0 |
| OpenTelemetry Collector (releases repo) | v0.162.0 |
| Jaeger | v2.22.0 |
