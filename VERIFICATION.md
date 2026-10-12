# Verification

What was run before this release, what passed, and what was **not** run. Nothing in
this file is a promise about your machine: run the same commands yourself, and treat
everything in the "Not verified here" table as untested until you have.

Checked on **2026-10-12** in a Linux container: Python 3.13.16, git 2.43.0,
Chromium 141.0.7390.37 (headless, for the browser tests).

## Passed

| Check | Command | Result |
|---|---|---|
| Lint and formatting | `python tasks.py lint` | Ruff: all checks passed; 84 files already formatted |
| Strict type checking | `python tasks.py typecheck` | mypy strict: no issues in 11 source files |
| Unit, API, agent, script and phase tests | `python tasks.py test` | 218 passed (unit 25, API 24, agent 31, scripts 11, phase self-checks 127); browser tests are run separately |
| Coverage of `src/` | (part of `python tasks.py test`) | 98% of 557 statements, branch coverage on |
| Browser end-to-end tests (Playwright) | `python tasks.py e2e` | 5 passed |
| YAML and JSON syntax | `python scripts/validate_files.py` | 27 YAML and 5 JSON files, 0 errors |
| Kubernetes manifests against the official v1.37.1 OpenAPI schema (strict) | `python scripts/validate_k8s.py infra/k8s` | 7 objects, 0 errors; 1 skipped (`kustomization.yaml` is Kustomize configuration, not a cluster object) |
| Dependency vulnerabilities | `python -m pip_audit --skip-editable` | No known vulnerabilities found |
| Python security lint | Bandit, medium severity and above (see `tasks.py audit`) | No findings |
| Repository audit (links, tool policy, no AI attribution) | `python tasks.py repo-audit` | 0 problems, 0 warnings |
| Live app smoke test | `python -m fullsend`, then `python scripts/smoke_test.py http://127.0.0.1:8000` | 5 of 5 checks passed |
| Graceful shutdown | Send SIGTERM to the running app | Lifespan "stopping" log written. Exit status 143 is expected: Uvicorn re-raises the signal after a clean shutdown |
| Commit-message hook | Phase 2 self-check, in a real temporary git repository | Bad header blocked, AI credit line blocked, good message accepted |
| GitHub Actions pins | `git ls-remote` against each action's repository | All 33 `uses:` references are pinned to full commit SHAs; all 15 action-and-commit pairs match their release tags |

On macOS and Windows, activate the virtual environment first
([Phase 0](phases/00-setup/README.md)); after that, every command above is the same
on all systems. For the browser tests, `python tasks.py setup` installs Playwright's
Chromium. Here a preinstalled Chromium was used through the `E2E_CHROMIUM_EXECUTABLE`
variable ([tests/e2e/conftest.py](tests/e2e/conftest.py)).

## Not verified here

These were written from each tool's official documentation, and their files were
parsed (YAML, JSON) where possible, but **they were not executed** before release.
The container had no reachable Docker daemon, these tools were not installed, and
its network only reached package registries and GitHub.

| Not run | Why | How to verify it yourself |
|---|---|---|
| `docker build`, running the image, its `HEALTHCHECK`, and `image_audit.py` on a real image | No Docker daemon | [Phase 3](phases/03-containers/README.md) |
| The Nginx lab (Phase 1) and the Prometheus/Grafana stack (`observability/compose.yaml`) | No Docker daemon | [Phase 1](phases/01-foundations/README.md), [Phase 6](phases/06-reliability/README.md) |
| kind cluster, `kubectl apply`, Helm lint, install, upgrade, test and rollback | kind, kubectl and Helm not installed | [Phase 5](phases/05-kubernetes-iac-cloud/README.md), Labs A and B; the `infra.yml` workflow runs the same steps |
| Argo CD sync | Needs a cluster | [Phase 5](phases/05-kubernetes-iac-cloud/README.md), Lab C |
| `terraform fmt`, `init`, `validate` and `plan`; the EKS lab | Terraform not installed; a plan needs AWS credentials and the lab costs money | `infra.yml` runs `fmt`, `init -backend=false` and `validate`; the EKS lab is in [infra/README.md](infra/README.md) |
| `promtool check rules` and `promtool test rules` on the alert rules | promtool not installed; the rule files were only parsed as YAML | [Phase 6](phases/06-reliability/README.md) |
| Every workflow in `.github/workflows` on GitHub, including CodeQL and dependency review | They only run on GitHub | Push your fork and open the **Actions** tab; Phase 4 walks through the first run |
| Python 3.14 and 3.15 | The container had Python 3.13.16 | CI tests 3.13 and 3.14, and 3.15 as allowed-to-fail |
| macOS and Windows commands in the lessons | Only Linux was available | Taken from each tool's official docs; please report any that fail (issue template "Bug or broken lab step") |
| External links (`repo_audit.py --external`) | No general internet access | The `links.yml` workflow runs it weekly |
| The dev container | Needs Docker | Open the repository in a dev container or Codespaces |
| The triage agent against the real GitHub API | Tested against a fake GitHub (`tests/agent/fake_github.py`) only | [Phase 7](phases/07-security-ai/README.md), with a read-only token on your fork |
| Sending traces to a real OpenTelemetry endpoint | Exporter set-up is unit-tested; no collector was running | [Phase 6](phases/06-reliability/README.md) |

## Re-run everything

| Step | Command (same on macOS and Windows, virtual environment active) |
|---|---|
| All fast checks | `python tasks.py check` |
| Browser tests | `python tasks.py e2e` |
| Repository audit | `python tasks.py repo-audit` |
| Also check external links | `python scripts/repo_audit.py --external` |
