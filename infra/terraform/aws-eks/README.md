# EKS lab (optional, costs money)

Creates a VPC (two availability zones, one NAT gateway) and an Amazon EKS cluster
running Kubernetes 1.37 with a managed node group of two `t3.medium` nodes.

## Before you start

| Check | Why |
|---|---|
| **Cost.** EKS charges $0.10 per cluster per hour in standard support (AWS EKS pricing page, read 2026-10-12), plus EC2 for the nodes, the NAT gateway, data transfer and any load balancers. Check the pricing pages for your region before applying. | A forgotten cluster keeps billing |
| **Set a budget alert** in AWS Budgets first | You hear about cost before the invoice |
| **Use a sandbox account**, not one that runs anything real | Mistakes stay contained |
| **Credentials** via IAM Identity Center (`aws configure sso`) rather than long-lived access keys | Short-lived credentials leak less |
| **Modules** come from the community `terraform-aws-modules` organisation, pinned to exact versions (VPC 6.7.3, EKS 21.29.0) | Read their READMEs; they are not maintained by HashiCorp or AWS |

## Run it

All commands run inside this folder, identical on macOS and Windows.

| Step | Command |
|---|---|
| Your settings | copy `terraform.tfvars.example` to `terraform.tfvars`, set `owner` |
| Check who you are | `aws sts get-caller-identity` |
| Init | `terraform init` |
| Plan to a file | `terraform plan -out=plan.out` |
| Guard the plan | `terraform show -json plan.out > plan.json` then `python ../../../phases/05-kubernetes-iac-cloud/tf_plan_guard.py plan.json` |
| Apply | `terraform apply plan.out` |
| Connect kubectl | run the command printed as `configure_kubectl` |
| Deploy the app | `helm install fullsend ../../helm/fullsend -n fullsend --create-namespace --set image.repository=ghcr.io/<owner-lowercase>/fullsend --set image.tag=latest` |

## Tear it down (do not skip)

| Step | Command |
|---|---|
| Remove what Kubernetes created in AWS (for example load balancers) | `helm uninstall fullsend -n fullsend` |
| Destroy the cluster and VPC | `terraform destroy` |
| Confirm | `aws eks list-clusters --region <region>` shows nothing; check the billing console the next day |

## Remote state

State is local by default, which is fine for one person in a lab. For a team,
rename [`backend.tf.example`](backend.tf.example) to `backend.tf`: it stores state
in S3 with S3-native locking (`use_lockfile = true`); HashiCorp marks the older
DynamoDB locking as deprecated.
