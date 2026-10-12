# Security policy

## Reporting a vulnerability

Please **do not** open a public issue for a security problem. Use GitHub's private
vulnerability reporting instead: on this repository, open the **Security** tab and
choose **Report a vulnerability**. Include what you found, how to reproduce it, and
the impact you expect.

If private reporting is not enabled on the copy you are looking at (for example a
fork), contact that repository's owner privately.

## Scope

| In scope | Out of scope |
|---|---|
| The FullSend app (`src/fullsend`), the triage agent (`src/ci_triage`) and the scripts | Vulnerabilities in third-party tools themselves; report those to their projects |
| The workflows in `.github/workflows` (for example token permissions or injection) | Findings that need a compromised developer machine first |
| The Kubernetes manifests, Helm chart and Terraform in `infra/` | Intentional lab features: `CHAOS_ERROR_RATE` and `CHAOS_LATENCY_MS` are fault-injection switches, and the fake tokens in tests are fake |

## What this repository does to stay safe

- GitHub Actions pinned to full commit SHAs; `GITHUB_TOKEN` read-only by default.
- Dependabot updates, dependency review on pull requests, CodeQL, pip-audit, Bandit.
- Container images scanned with Trivy before they are published; non-root images.
- `restricted` Pod Security Standard and a NetworkPolicy in the Kubernetes manifests.
- No long-lived cloud credentials: the cloud lab uses short-lived credentials (OIDC or SSO).

The reasoning behind each control is in [Phase 7](phases/07-security-ai/README.md).

## Supported versions

Only the latest commit on `main` is maintained.
