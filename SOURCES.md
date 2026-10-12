# Sources

Everything this pack states as fact links back to one of these sources. Official
documentation came first; articles and reports were used only where no official
source exists (hiring trends, for example), and are labelled as such.
All pages were read on **2026-10-12** unless a date says otherwise.

## Contents

- [Official documentation used for commands and versions](#official-documentation)
- [Hiring signals](#hiring-signals)
- [AI in DevOps](#ai-in-devops)
- [Languages](#languages)
- [Security incident: Trivy, March 2026](#security-incident-trivy-march-2026)
- [Licences](#licences)
- [Learning repositories referenced](#learning-repositories-referenced)

## Official documentation

| Topic | Source |
|---|---|
| Python releases and support status | <https://devguide.python.org/versions/> · <https://www.python.org/downloads/release/python-3150/> |
| Virtual environments (activation table, PowerShell execution policy) | <https://docs.python.org/3/library/venv.html> |
| Python on Windows (install manager, `py install`, winget ID) | <https://docs.python.org/3/using/windows.html> |
| Homebrew install command and supported macOS | <https://brew.sh/> · `python@3.14` formula: <https://formulae.brew.sh/formula/python@3.14> |
| Git for macOS and Windows | <https://git-scm.com/install/mac> · <https://git-scm.com/install/windows> |
| WinGet availability | <https://learn.microsoft.com/en-us/windows/package-manager/winget/> |
| WSL install | <https://learn.microsoft.com/en-us/windows/wsl/install> |
| Docker Desktop (requirements, licence terms) | <https://docs.docker.com/desktop/setup/install/mac-install/> · <https://docs.docker.com/desktop/setup/install/windows-install/> |
| Compose file name (`compose.yaml`) | <https://docs.docker.com/compose/intro/compose-application-model/> |
| Python Docker Official Image tags | <https://github.com/docker-library/official-images/blob/master/library/python> |
| kubectl install and version skew | <https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/> · <https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/> |
| Kubernetes OpenAPI schema used by `validate_k8s.py` | <https://github.com/kubernetes/kubernetes/tree/v1.37.1/api/openapi-spec> |
| kind install, node images, network policy support | <https://kind.sigs.k8s.io/docs/user/quick-start/> · <https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0> · <https://github.com/kubernetes-sigs/kind/releases/tag/v0.24.0> |
| Helm 4 install and compatibility | <https://helm.sh/docs/intro/install/> · <https://helm.sh/docs/overview> |
| Argo CD install | <https://argo-cd.readthedocs.io/en/stable/getting_started/> |
| Terraform install, S3 backend, licence | <https://developer.hashicorp.com/terraform/install> · <https://developer.hashicorp.com/terraform/language/backend/s3> · <https://github.com/hashicorp/terraform/blob/main/LICENSE> |
| Terraform 1.10 S3 native locking | <https://github.com/hashicorp/terraform/blob/v1.10.0/CHANGELOG.md> |
| EKS and VPC modules (inputs, version constraints) | <https://github.com/terraform-aws-modules/terraform-aws-eks/tree/v21.29.0> · <https://github.com/terraform-aws-modules/terraform-aws-vpc/tree/v6.7.3> |
| Amazon EKS Kubernetes versions and pricing | <https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html> · <https://aws.amazon.com/eks/pricing/> |
| AWS CLI v2 install | <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html> |
| CKA exam format | <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/> |
| Playwright for Python (install, running tests) | <https://playwright.dev/python/docs/intro> · <https://playwright.dev/python/docs/running-tests> |
| Prometheus Python client with ASGI and FastAPI | <https://prometheus.github.io/client_python/exporting/http/asgi/> · <https://prometheus.github.io/client_python/exporting/http/fastapi-gunicorn/> |
| Prometheus image and config path | <https://prometheus.io/docs/prometheus/latest/installation/> |
| Grafana Docker image and provisioning | <https://grafana.com/docs/grafana/latest/setup-grafana/configure-docker/> · <https://grafana.com/docs/grafana/latest/administration/provisioning/> |
| SLO alerting (multiwindow, multi-burn-rate; Table 5-8) | <https://sre.google/workbook/alerting-on-slos/> |
| DORA software delivery metrics | <https://dora.dev/guides/dora-metrics/> |
| MCP Python SDK v2 (MCPServer, in-process Client, migration) | <https://github.com/modelcontextprotocol/python-sdk> · <https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md> |
| GitHub REST API: workflow runs, jobs, logs, API versions | <https://docs.github.com/en/rest/actions/workflow-runs> · <https://docs.github.com/en/rest/actions/workflow-jobs> · <https://docs.github.com/en/rest/about-the-rest-api/api-versions> |
| GitHub Actions secure use (SHA pinning, token permissions, script injection) | <https://docs.github.com/en/actions/reference/security/secure-use> |
| Artifact attestations (next step in Phase 7) | <https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations> |
| Commit e-mail and the no-reply address | <https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address> · <https://docs.github.com/en/account-and-profile/reference/email-addresses-reference> |

Version numbers and commit SHAs were read from each project's own release tags
(with `git ls-remote`) and from PyPI. They are listed in [VERSIONS.md](VERSIONS.md).

## Hiring signals

The question was "what do the top 50 companies hire for?". Postings from all 50 could
not be collected; postings from **two** of them (Google and NVIDIA) were read
directly, plus other public postings and 2026 hiring reports. Treat this as a
sample, not a survey.

**Job postings (primary sources)**

| Employer | Posting | What it asks for |
|---|---|---|
| Google | [Staff Site Reliability Engineer](https://jobs.anitab.org/companies/google-24698/jobs/82488783-staff-site-reliability-engineer) (posted 2026-06-12) | Reliability of data systems behind Google's AI work; listed pay USD 207k–301k plus equity |
| Google | [Staff SRE, Quota SRE](https://jobs.anitab.org/companies/google-24698/jobs/86516610-staff-site-reliability-engineer-quota-sre) | 8 years in software, systems or site reliability engineering |
| Google | [Senior SRE, Software Engineer (Ireland)](https://anyreality.jobboardly.com/jobs/senior-site-reliability-engineer-software-engineer-6d73b440) | Software development, distributed-systems troubleshooting; SRE as "operations as a software problem" |
| Google | [SRE, Technical Infrastructure (Bengaluru)](https://careers.google.com/jobs/results/138177454597382854-site-reliability-engineer) | Data structures and algorithms, software development in Python, C++ or Java |
| Google | [SRE, Google Distributed Cloud](https://jobs.anitab.org/companies/google-24698/jobs/63845140-site-reliability-engineer-google-distributed-cloud-connected-sre) | SLOs, monitoring, rollout safety, production safety systems |
| NVIDIA | [Senior DevOps Engineer, E-commerce](https://jobs.anitab.org/companies/nvidia/jobs/86334581-senior-devops-engineer-e-commerce) (posted 2026-07-15) | Expert Terraform (state, workspaces, modules); EKS, Docker, Helm; Python; AI-powered observability; "demonstrated use of AI tools"; USD 176k–333.5k plus equity |
| NVIDIA | [Senior SRE Engineer](https://jobs.anitab.org/companies/nvidia/jobs/84994064-senior-sre-engineer) | CI as a Service on GitLab CI and GitHub Actions; SLO/SLI, incident command; deep Kubernetes; Python, Go or Bash; CKA, CKS, CKAD preferred |
| NVIDIA | [Senior DevOps and SRE Engineer](https://jobs.anitab.org/companies/nvidia/jobs/54415016-senior-devops-and-sre-engineer) | Kubernetes platform engineering; Terraform and Ansible; Python or Go |
| Not named | [SRE/DevOps Engineer (contract, Dice)](https://www.dice.com/job-detail/d62f34a4-371c-4d1d-8f97-a8d6d243400f) | Python as the primary language; engineers "already incorporating AI into their daily development process" |
| Not named | [DevOps Engineer, AI Infrastructure and Platforms](https://insightglobal.com/jobs/find_a_job/job-530720) | Kubernetes security, Terraform or Pulumi, Python, container security scanning, GPU workloads |

**Reports and articles (secondary sources; their numbers are their own)**

| Source | Used for |
|---|---|
| [Learners Ink: DevOps vs SRE vs Platform Engineer in 2026](https://www.learnersink.com/blog/devops-engineer-vs-sre-vs-platform-engineer) | Title shift; its growth figures were not verified |
| [RemoteStack: in-demand DevOps skills for remote jobs, 2026](https://remotestack.in/blog/most-in-demand-devops-skills-remote-2026) | Kubernetes as the top skill in its listings; "DevOps Engineer" titles fading |
| [KORE1: Platform Engineer salary guide 2026](https://www.kore1.com/platform-engineer-salary-guide-2026/) | Overlap between DevOps, SRE and Platform titles |
| [Axial Search: MLOps hiring 2026](https://axialsearch.com/insights/mlops-hiring) | MLOps postings steady, not spiking |

## AI in DevOps

| Claim | Source |
|---|---|
| About 90% of software professionals use AI at work; AI is an "amplifier" | [Google: DORA 2025 report](https://blog.google/technology/developers/dora-report-2025/) · [InfoQ on DORA 2025](https://www.infoq.com/news/2025/09/dora-state-of-ai-in-dev-2025) |
| Agents across the delivery lifecycle, with guardrails | [DZone: six trends shaping 2026](https://dzone.com/articles/software-devops-trends-shaping-2026) |
| MCP servers for DevOps tools | [InfoWorld: 10 MCP servers for DevOps](https://www.infoworld.com/article/4096223/10-mcp-servers-for-devops.html) · [Mirantis: DevOps MCP servers](https://www.mirantis.com/blog/18-best-devops-mcp-servers/) · [Model Context Protocol](https://modelcontextprotocol.io/) |
| AI SRE agents (vendor figure: 25% faster resolution) | [New Relic press release, 2026-02-24](https://newrelic.com/press-release/20260224) |

## Languages

| Claim | Source |
|---|---|
| Python 57.9%, Bash/Shell 48.7%, PowerShell 23.2%, Go 16.4% of developers (Stack Overflow 2025 survey) | [Statista summary of the Stack Overflow 2025 survey](https://www.statista.com/statistics/793628/worldwide-developer-survey-most-used-languages/) |
| Python and Go as the best languages for DevOps; Groovy in Jenkins | [DevOpsCube: programming languages for DevOps](https://devopscube.com/programming-languages-devops/) |

## Security incident: Trivy, March 2026

| Source | Used for |
|---|---|
| [Aqua Security advisory](https://www.aquasec.com/blog/trivy-supply-chain-attack-what-you-need-to-know) | Timeline, safe versions, "pinning to full commit SHAs remains the only truly immutable protection" |
| [NVD: CVE-2026-33634](https://nvd.nist.gov/vuln/detail/CVE-2026-33634) | CVE details, CISA KEV listing, remediation steps |
| [GitHub advisory GHSA-69fq-xp46-6x23](https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23) | The vendor's advisory record |
| [Snyk analysis](https://snyk.io/articles/trivy-github-actions-supply-chain-compromise/) | How the malicious entrypoint worked |
| [trivy-action v0.36.0 release](https://github.com/aquasecurity/trivy-action/releases/tag/v0.36.0) | Released after the incident; pins `setup-trivy` by hash |

## Licences

| Source | Used for |
|---|---|
| [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) | This repository's licence (patent grant, contributions, trademarks) |
| [choosealicense.com](https://choosealicense.com/licenses/) | MIT vs Apache-2.0 comparison |
| Each tool's `LICENSE` file in its official repository | The licence column in [TOOLS.md](TOOLS.md) |

## Learning repositories referenced

| Repository | Licence noted on its page |
|---|---|
| [milanm/DevOps-Roadmap](https://github.com/milanm/DevOps-Roadmap) | Apache-2.0 |
| [MichaelCade/90DaysOfDevOps](https://github.com/MichaelCade/90DaysOfDevOps) | CC BY-NC-SA 4.0 |
| [bregman-arie/devops-exercises](https://github.com/bregman-arie/devops-exercises) | Creative Commons legal code with a non-commercial condition (its `LICENSE` file) |
| [bregman-arie/system-design-notebook](https://github.com/bregman-arie/system-design-notebook) | CC BY-NC-ND 3.0 |

No content from these repositories is copied here; they are linked for further study.
