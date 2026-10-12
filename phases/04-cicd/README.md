# Phase 4 · CI/CD: every change tested, scanned and shipped the same way

**Time:** 2 weeks · **Roadmap map:** milanm/DevOps-Roadmap step 9 (CI/CD)

**You finish with:** a pipeline you can explain job by job, secured the way
GitHub's own security guide recommends, publishing an image to GitHub Container
Registry, plus your first DORA numbers.

## Why hiring teams care

NVIDIA's senior SRE posting describes owning an internal "CI as a Service platform"
on GitLab CI and GitHub Actions, run "like a product". CI/CD is where DevOps
engineers spend much of their week, and where supply-chain attacks land (Phase 7).

---

## 1. Words first

| Term | Meaning |
|---|---|
| Continuous integration (CI) | Every push is built and tested automatically, so problems surface in minutes, not at release time |
| Continuous delivery | Every change that passes CI *could* go to production with one approved click |
| Continuous deployment | Every change that passes CI *does* go to production automatically |
| Workflow · job · step | A workflow file holds jobs; each job runs on a fresh runner machine; each step is a command or an action |
| Action | A reusable step published in a repository (for example `actions/checkout`) |
| Artifact | A file a job keeps after it finishes (test reports, traces, a built package) |

## 2. This repository's pipelines

```text
push / pull request
   │
   ├─ lint ─────── Ruff · mypy · repo audit · YAML/JSON/Kubernetes schema
   ├─ test ─────── pytest on Python 3.13, 3.14 (+3.15 allowed to fail) · coverage ≥ 90%
   ├─ e2e ──────── Playwright in Chromium · traces kept on failure
   ├─ security ─── pip-audit · Bandit
   │
   └─ image ────── needs all four ── build → Trivy scan → push to GHCR (main only)

infra changes ─── Terraform fmt/validate · Helm lint · render → schema check · deploy to kind → smoke test
weekly ────────── CodeQL · external link check        pull requests ── dependency review
```

| File | Read it for |
|---|---|
| [`ci.yml`](../../.github/workflows/ci.yml) | The main pipeline above |
| [`infra.yml`](../../.github/workflows/infra.yml) | Infrastructure checks and a real deploy to a throwaway kind cluster |
| [`codeql.yml`](../../.github/workflows/codeql.yml) | GitHub's code scanning |
| [`dependency-review.yml`](../../.github/workflows/dependency-review.yml) | Blocks PRs that add known-vulnerable dependencies |
| [`links.yml`](../../.github/workflows/links.yml) | Weekly check that lesson links still work |
| [`dependabot.yml`](../../.github/dependabot.yml) | Weekly update PRs for Python packages, actions, Docker base image, Terraform |

## 3. Securing a pipeline: four rules from GitHub's own guide

GitHub's "Secure use reference" for Actions is the source for each rule; the
self-check at the end of this phase tests that every workflow here follows them.

| Rule | What GitHub's guide says | How this repo applies it |
|---|---|---|
| Pin actions to a commit SHA | Pinning "helps mitigate the risk of a bad actor adding a backdoor to the action's repository". | Every `uses:` is `owner/action@<40-character SHA> # vX.Y.Z`. Dependabot proposes updates. |
| Least-privilege `GITHUB_TOKEN` | Grant "the minimum required permissions"; read-only contents by default. | Every workflow starts with `permissions: contents: read`; only the image job adds `packages: write`. |
| No script injection | Pass untrusted input such as PR titles through an environment variable instead of `${{ }}` inside `run:`. | No workflow interpolates PR titles, branch names or issue text into shell commands. |
| OIDC instead of stored cloud keys | Workflows can authenticate to the cloud directly and stop storing long-lived secrets. | The optional AWS deploy below uses OIDC; no AWS keys are stored anywhere. |

Also: `actions/checkout` runs with `persist-credentials: false`, so later steps
cannot reuse the token by accident, and every job has a `timeout-minutes`.

## 4. Lab: make the pipeline yours

| Step | Where |
|---|---|
| 1. Push your fork's `main`. If GitHub shows a banner that workflows are disabled on the fork, open the **Actions** tab and enable them. | GitHub → your fork → Actions |
| 2. Watch the **CI** workflow. Open a job, expand a step, download the `test-reports-3.14` artifact. | Actions → CI run |
| 3. Break it on purpose: on a branch, change an assertion in `tests/unit/test_store.py`, push, open a PR. CI goes red. Fix it, push again. | Pull requests |
| 4. Protect `main`: add a ruleset that requires a pull request and the CI checks to pass before merging. | Settings → Rules → Rulesets |
| 5. After a merge to `main`, find your image. GHCR names are lowercase: `ghcr.io/<owner-lowercase>/fullsend`. Check the package's visibility before Phase 5's GitOps lab; a cluster needs a public image or a pull secret. | Your profile → Packages |
| 6. Pull and run what CI built. | `docker run --rm -p 127.0.0.1:8000:8000 ghcr.io/<owner-lowercase>/fullsend:latest` |

## 5. Deployment strategies

| Strategy | How it works | Use when |
|---|---|---|
| Rolling | Replace pods a few at a time (Kubernetes default; this repo uses `maxUnavailable: 0`) | Most stateless services |
| Blue/green | Run the new version beside the old, switch traffic at once, keep the old one for instant rollback | Risky releases that need a fast, clean rollback |
| Canary | Send a small share of traffic to the new version, watch error rates, then widen | High-traffic services with good metrics (Phase 6) |
| Feature flags | Ship code switched off; turn it on separately from the deploy | Separating deploy from release |

## 6. Optional: deploy to AWS without stored keys (OIDC)

When you run the Phase 5 EKS lab, CI can deploy with short-lived credentials. One
time in AWS, create an IAM OIDC identity provider for GitHub and a role that trusts
**only** your repository and branch (AWS and GitHub both document this). Then a job looks like this:

```yaml
  deploy:
    needs: [image]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
      id-token: write # lets the job request an OIDC token; nothing else
    steps:
      - uses: aws-actions/configure-aws-credentials@e1253824e5c10ff9df46874f81ed3ec929e19cfd # v6.3.0
        with:
          role-to-assume: arn:aws:iam::<account-id>:role/<deploy-role>
          aws-region: us-east-1
      - run: aws eks update-kubeconfig --region us-east-1 --name fullsend
      # then: helm upgrade --install … with the image tag CI just pushed
```

## 7. Measure delivery: DORA metrics

DORA's guide now lists five software delivery metrics, in two groups:

| Group | Metric | Meaning |
|---|---|---|
| Throughput | Change lead time | Commit to running in production |
| Throughput | Deployment frequency | How often you deploy |
| Throughput | Failed deployment recovery time | How long to recover from a deployment that failed |
| Instability | Change fail rate | Share of deployments needing immediate intervention |
| Instability | Deployment rework rate | Share of deployments that were unplanned, caused by a production incident |

Two ways to measure in this repo:

| Tool | Gives you |
|---|---|
| [`dora_from_git.py`](dora_from_git.py): `python phases/04-cicd/dora_from_git.py --days 90` | Deployment frequency and change lead time from release tags |
| FullSend's `GET /api/v1/dora` | Change fail rate from recorded deployments |

Try it: tag a release (`git tag -a v1.0.1 -m "release"`, then `git push origin v1.0.1`) and run the script.

## Check yourself

```text
python -m pytest phases/04-cicd
```

These checks also guard the workflows: an unpinned action, broader default
permissions, a checkout that keeps credentials, or a job without a timeout fails them.

## Interview questions

1. What is the difference between continuous delivery and continuous deployment?
2. Why pin a GitHub Action to a commit SHA rather than `@v7`? What do you trade away?
3. A workflow uses `${{ github.event.pull_request.title }}` inside `run:`. What is the risk, and the fix?
4. How would you give a pipeline access to AWS without storing access keys?
5. Your CI takes 25 minutes. Walk me through how you would make it faster.
6. Which DORA metric would you improve first on a team that deploys monthly, and how?
7. When is a canary release worth its complexity?

## AI exercise (with guardrails)

Give an assistant `ci.yml` and ask it to find security or reliability problems.
Check every claim against GitHub's "Secure use reference". Then ask it to add a new
job, and verify that its suggestion pins actions by SHA, keeps `permissions`
minimal, and sets a timeout. Assistants often produce `@v4`-style tags from older
examples; the self-check catches that.

## Done when

- [ ] CI is green on your fork and protects `main` through a ruleset
- [ ] An image built by CI runs on your laptop
- [ ] You can explain every job and every permission in `ci.yml`
- [ ] You have a DORA baseline from `dora_from_git.py`
- [ ] `python -m pytest phases/04-cicd` passes

## Official docs

- GitHub Actions secure use reference: <https://docs.github.com/en/actions/reference/security/secure-use>
- Workflow syntax: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>
- Publishing images to GHCR from Actions: <https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions>
- Rulesets: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets>
- Dependabot version updates: <https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/about-dependabot-version-updates>
- `aws-actions/configure-aws-credentials`: <https://github.com/aws-actions/configure-aws-credentials>
- DORA metrics guide: <https://dora.dev/guides/dora-metrics/>

Previous: [Phase 3](../03-containers/README.md) · Next: [Phase 5 · Kubernetes, IaC and cloud](../05-kubernetes-iac-cloud/README.md)
