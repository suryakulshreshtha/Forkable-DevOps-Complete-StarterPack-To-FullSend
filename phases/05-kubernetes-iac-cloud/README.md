# Phase 5 · Kubernetes, infrastructure as code, and the cloud

**Time:** 4–6 weeks · **Roadmap map:** milanm/DevOps-Roadmap steps 7 (orchestration), 8 (infrastructure as code), 11 (one cloud provider)

**You finish with:** the app running on a local Kubernetes cluster three ways (plain
manifests, Helm, GitOps with Argo CD), an EKS cluster defined in Terraform that
you can create and destroy safely, and a guard that blocks dangerous plans.

## Why hiring teams care

This is the core of every posting we read. NVIDIA's SRE and DevOps postings ask for:

- deep Kubernetes administration: CRDs and operators, autoscaling, RBAC, network policies
- "expert-level" Terraform, including state management, workspaces and modules
- AWS EKS, and the CKA, CKS and CKAD certifications as a plus

---

## Install the cluster tools

### macOS

| Tool | Command (Terminal) |
|---|---|
| kubectl | `brew install kubectl` |
| kind | `brew install kind` |
| Helm | `brew install helm` |
| Terraform | `brew tap hashicorp/tap` then `brew install hashicorp/tap/terraform` |
| AWS CLI v2 (cloud lab only) | `curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"` then `sudo installer -pkg AWSCLIV2.pkg -target /` |

### Windows

| Tool | Command (PowerShell) |
|---|---|
| kubectl | `winget install -e --id Kubernetes.kubectl` |
| kind | `winget install Kubernetes.kind` |
| Helm | `winget install Helm.Helm` |
| Terraform | Download the Windows AMD64 zip from the [Terraform install page](https://developer.hashicorp.com/terraform/install), unzip `terraform.exe` into a folder on your PATH |
| AWS CLI v2 (cloud lab only) | `msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi` (needs admin rights) |

### Dev container / Linux

kubectl, Helm and Terraform come with the dev container. kind on Linux x86-64
(from kind's quick start): `curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.33.0/kind-linux-amd64`,
then `chmod +x ./kind` and `sudo mv ./kind /usr/local/bin/kind`.

Then check: `python phases/00-setup/doctor.py`. Notes: Helm says package-manager
builds are maintained by the community, not the Helm project; and keep kubectl within
one minor version of your cluster (Kubernetes version skew policy).

---

## 1. Kubernetes in one table

| Object | Job | In this repo |
|---|---|---|
| Pod | One or more containers scheduled together | Created by the Deployment |
| Deployment | Keeps N identical pods running; rolls out new versions | [`infra/k8s/deployment.yaml`](../../infra/k8s/deployment.yaml) |
| Service | A stable name and IP in front of changing pods | [`service.yaml`](../../infra/k8s/service.yaml) |
| ConfigMap / Secret | Configuration and sensitive values injected into pods | [`configmap.yaml`](../../infra/k8s/configmap.yaml) |
| Namespace | A boundary for names, quotas and policies | [`namespace.yaml`](../../infra/k8s/namespace.yaml) |
| Probes | startup: has it booted? liveness: restart it? readiness: send it traffic? | All three, against `/healthz/*` |
| Requests and limits | Requests reserve capacity for scheduling; a memory limit stops a leak taking the node down | Memory limit set; no CPU limit, which avoids throttling a latency-sensitive API (a debated trade-off: know both sides) |
| HorizontalPodAutoscaler | Adds or removes pods based on load | [`hpa.yaml`](../../infra/k8s/hpa.yaml) (needs Metrics Server) |
| PodDisruptionBudget | Keeps pods running during node drains | [`pdb.yaml`](../../infra/k8s/pdb.yaml) |
| NetworkPolicy | Allows only the traffic you list | [`networkpolicy.yaml`](../../infra/k8s/networkpolicy.yaml) |
| Pod Security Standards | Namespace labels that reject unsafe pods | `restricted` is enforced on the namespace |
| RBAC | Who may do what to which objects | The pod gets no API token at all (`automountServiceAccountToken: false`) |
| CRDs and operators | New object types plus a controller that acts on them | Argo CD's `Application` in Lab C is one |

Every manifest here is checked against the **official Kubernetes v1.37 API schema**
by [`scripts/validate_k8s.py`](../../scripts/validate_k8s.py), in strict mode, so a
misspelled field fails CI: `python tasks.py validate`.

## 2. Lab A: run it on kind, then break it

Same commands in macOS Terminal and Windows PowerShell (Docker Desktop must be running).

| Step | Command |
|---|---|
| Create a 2-node cluster (node image pinned by digest) | `kind create cluster --config infra/kind/kind-config.yaml` |
| Build the image | `docker build -t fullsend:dev .` |
| Copy it into the cluster's nodes | `kind load docker-image fullsend:dev --name fullsend` |
| Deploy everything | `kubectl apply -k infra/k8s` |
| Wait for the rollout | `kubectl -n fullsend rollout status deploy/fullsend` |
| Look around | `kubectl -n fullsend get pods -o wide` · `kubectl -n fullsend describe deploy fullsend` |
| Reach it (leave running) | `kubectl -n fullsend port-forward svc/fullsend 8080:80` |
| Smoke test (another terminal) | `python scripts/smoke_test.py http://127.0.0.1:8080` |
| Rollout report | `kubectl get deployments -A -o json > deploys.json` then `python phases/05-kubernetes-iac-cloud/rollout_report.py deploys.json` |

Now break it, one thing at a time, and explain what you see:

| Experiment | Command | What to notice |
|---|---|---|
| Self-healing | `kubectl -n fullsend delete pod <one-pod-name>` | A replacement appears; the Service never stops answering |
| Bad release | `kubectl -n fullsend set image deploy/fullsend fullsend=fullsend:does-not-exist` | New pod stuck in `ErrImagePull`; because `maxUnavailable: 0`, the old pods keep serving |
| Roll back | `kubectl -n fullsend rollout undo deploy/fullsend` | Back to the working version |
| Change config | Edit `CHAOS_ERROR_RATE` in `infra/k8s/configmap.yaml` to `"0.3"`, `kubectl apply -k infra/k8s`, then `kubectl -n fullsend rollout restart deploy/fullsend` | Env vars from a ConfigMap only load at pod start, hence the restart |
| Restricted pod security | `kubectl -n fullsend run quick-test --image=fullsend:dev` | Rejected: a bare `kubectl run` pod does not drop capabilities, set a seccomp profile or forbid privilege escalation, and the error lists each `restricted` rule it breaks |
| Clean up | `kind delete cluster --name fullsend` | |

## 3. Lab B: package it with Helm

The chart in [`infra/helm/fullsend`](../../infra/helm/fullsend) renders the same
objects with values you can change per environment, and
[`values.schema.json`](../../infra/helm/fullsend/values.schema.json) rejects bad values
before anything reaches the cluster. This pack uses Helm 4 (4.3.0); Helm's docs
say v2 charts, like this one, keep working unchanged.

| Step | Command |
|---|---|
| Lint | `helm lint infra/helm/fullsend --strict` |
| See exactly what would be applied | `helm template demo infra/helm/fullsend` |
| Validate the rendered YAML (macOS) | `helm template demo infra/helm/fullsend \| python scripts/validate_k8s.py -` |
| Same on Windows | `helm template demo infra/helm/fullsend > rendered.yaml` then `python scripts/validate_k8s.py rendered.yaml` |
| Install (image from Lab A) | `helm install demo infra/helm/fullsend -n helm-demo --create-namespace --set image.tag=dev` |
| Upgrade | `helm upgrade demo infra/helm/fullsend -n helm-demo --set image.tag=dev --set replicaCount=3` |
| History and rollback | `helm history demo -n helm-demo` then `helm rollback demo 1 -n helm-demo` |
| Built-in test | `helm test demo -n helm-demo` |
| Schema stops a bad value | `helm install bad infra/helm/fullsend --set app.chaosErrorRate=2` fails before touching the cluster |
| Remove | `helm uninstall demo -n helm-demo` |

## 4. Lab C: GitOps with Argo CD

GitOps means the cluster pulls its desired state from Git; nobody runs
`kubectl apply` by hand. Argo CD is a CNCF project that does this. You need the
image CI pushed to GHCR in Phase 4, readable by the cluster (public package or a pull secret).

| Step | Command |
|---|---|
| Fresh cluster | `kind create cluster --config infra/kind/kind-config.yaml` |
| Install Argo CD (official getting-started commands) | `kubectl create namespace argocd` then `kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml` |
| Wait for it | `kubectl -n argocd rollout status deploy/argocd-server` |
| Point it at **your** fork | Edit [`infra/argocd/application.yaml`](../../infra/argocd/application.yaml): replace `YOUR-GITHUB-USER` (and the lowercase GHCR owner), commit, push |
| Register the app | `kubectl apply -n argocd -f infra/argocd/application.yaml` |
| UI (leave running) | `kubectl port-forward svc/argocd-server -n argocd 8443:443`, open <https://127.0.0.1:8443> (self-signed certificate warning is expected locally) |
| Admin password | `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"`, then decode it the same way on any OS: `python -c "import base64,sys; print(base64.b64decode(sys.argv[1]).decode())" <value>` |

Then: change `replicaCount` in the Application's values in Git and push. Argo CD
syncs it. Scale by hand with `kubectl -n fullsend-gitops scale deploy --all --replicas=1`
and watch `selfHeal` put it back. That is the point: Git is the source of truth.

## 5. Terraform: infrastructure you can review

| Idea | Meaning |
|---|---|
| Provider | Plugin that talks to an API (AWS here) |
| Module | Reusable bundle of resources; this lab uses the community `terraform-aws-modules` VPC and EKS modules, pinned to exact versions |
| State | Terraform's record of what exists. Never commit it (`.gitignore` covers it); share it through a remote backend with locking |
| Plan → apply | Plan shows the diff; apply does it. Always read the plan |
| Remote state locking | The S3 backend's `use_lockfile = true` is the current method; HashiCorp marks DynamoDB locking deprecated ([`backend.tf.example`](../../infra/terraform/aws-eks/backend.tf.example)) |
| Drift | Reality changed outside Terraform; the next plan shows it |
| Licence | Terraform 1.6 and later is under the Business Source License (production use is allowed unless you offer it to third parties to compete with IBM's paid versions). OpenTofu is a fork of Terraform under the Linux Foundation, if you need an open-source licence. |

**Guard rail you will use for real:** [`tf_plan_guard.py`](tf_plan_guard.py) reads
the plan JSON and fails if anything would be deleted or replaced. Replacing a VPC
or EKS cluster can never be waved through with a flag.

## 6. Lab D (optional, costs money): EKS on AWS

Read [`infra/terraform/aws-eks/README.md`](../../infra/terraform/aws-eks/README.md)
first: it covers cost, permissions and the teardown you **must** run. In short:

| Step | Command (run inside `infra/terraform/aws-eks`) |
|---|---|
| Configure credentials | `aws configure sso` (or your organisation's method), then `aws sts get-caller-identity` |
| Your variables | Copy `terraform.tfvars.example` to `terraform.tfvars` and set `owner` |
| Init and plan | `terraform init` then `terraform plan -out=plan.out` |
| Guard the plan | `terraform show -json plan.out > plan.json` then `python ../../../phases/05-kubernetes-iac-cloud/tf_plan_guard.py plan.json` |
| Apply (15–20 minutes) | `terraform apply plan.out` |
| Use it | Run the `configure_kubectl` output command, then the Helm install from Lab B with `--set image.repository=ghcr.io/<owner-lowercase>/fullsend --set image.tag=latest` |
| **Destroy when done** | `terraform destroy` |

## The Python tools in this phase

| Script | What it does |
|---|---|
| [`rollout_report.py`](rollout_report.py) | Finds deployments that are stuck, mid-rollout or not ready, from `kubectl … -o json` |
| [`tf_plan_guard.py`](tf_plan_guard.py) | Blocks Terraform plans that delete or replace resources |
| [`scripts/validate_k8s.py`](../../scripts/validate_k8s.py) | Validates manifests against the official Kubernetes API schema |

## Check yourself

```text
python -m pytest phases/05-kubernetes-iac-cloud
```

## Interview questions

1. Liveness, readiness and startup probes: what does each failure cause?
2. A rollout is stuck. Walk me through your first five commands.
3. Why might you set a memory limit but no CPU limit?
4. What problem does a PodDisruptionBudget solve during a node upgrade?
5. Where should Terraform state live for a team, and why does it need locking?
6. A plan wants to replace your database. What do you do before anything else?
7. Helm versus plain manifests versus GitOps: when would you choose each?
8. How do you give a pod access to AWS without static keys? (Research EKS Pod Identity.)

## AI exercise (with guardrails)

Ask an assistant to add a `Secret` and mount it into the Deployment. Validate the
result with `python scripts/validate_k8s.py`, check it against the `restricted`
pod security policy, and render it through Helm. **Never** let an assistant run
`terraform apply` or `kubectl` against a real cluster: read every command, run it yourself.

## Done when

- [ ] Labs A to C done; you broke and repaired the deployment yourself
- [ ] You can explain every field in `infra/k8s/deployment.yaml`
- [ ] `tf_plan_guard.py` has read a real plan (Lab D) or the test fixtures
- [ ] If you ran Lab D: `terraform destroy` completed and the AWS bill shows no running EKS cluster
- [ ] `python -m pytest phases/05-kubernetes-iac-cloud` passes
- [ ] Stretch: book the CKA. It is performance-based, online-proctored, two hours, from the Linux Foundation and CNCF

## Official docs

- Kubernetes concepts: <https://kubernetes.io/docs/concepts/>
- Probes: <https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/>
- Pod Security Standards: <https://kubernetes.io/docs/concepts/security/pod-security-standards/>
- kubectl install (macOS / Windows): <https://kubernetes.io/docs/tasks/tools/install-kubectl-macos/> · <https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/>
- kind quick start: <https://kind.sigs.k8s.io/docs/user/quick-start/>
- Helm docs and install: <https://helm.sh/docs/> · <https://helm.sh/docs/intro/install/>
- Argo CD getting started: <https://argo-cd.readthedocs.io/en/stable/getting_started/>
- Terraform install and S3 backend: <https://developer.hashicorp.com/terraform/install> · <https://developer.hashicorp.com/terraform/language/backend/s3>
- Terraform plan JSON format: <https://developer.hashicorp.com/terraform/internals/json-format>
- OpenTofu: <https://opentofu.org/>
- Amazon EKS Kubernetes versions and pricing: <https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html> · <https://aws.amazon.com/eks/pricing/>
- AWS CLI install: <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>
- CKA: <https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/>

Previous: [Phase 4](../04-cicd/README.md) · Next: [Phase 6 · Reliability](../06-reliability/README.md)
