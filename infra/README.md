# Infrastructure

| Folder | What it is | Lesson |
|---|---|---|
| [`k8s/`](k8s/) | Plain Kubernetes manifests applied with `kubectl apply -k infra/k8s` | Phase 5, Lab A |
| [`kind/`](kind/) | Local two-node cluster config, node image pinned by digest | Phase 5 |
| [`helm/fullsend/`](helm/fullsend/) | Helm chart with a values schema and a `helm test` hook | Phase 5, Lab B |
| [`argocd/`](argocd/) | Argo CD `Application` for GitOps from your fork | Phase 5, Lab C |
| [`terraform/aws-eks/`](terraform/aws-eks/) | VPC and EKS cluster on AWS (costs money) | Phase 5, Lab D |

All Kubernetes YAML is validated against the official Kubernetes v1.37.1 API schema
in strict mode (`python tasks.py validate`). The **Infrastructure** workflow
additionally lints and renders the chart, validates Terraform, and deploys both
the manifests and the chart to a throwaway kind cluster on every change.
