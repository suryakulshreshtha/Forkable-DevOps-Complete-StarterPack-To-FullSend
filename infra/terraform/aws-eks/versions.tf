terraform {
  # 1.10+ is needed for S3 native state locking (use_lockfile) shown in backend.tf.example.
  required_version = ">= 1.10.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.68" # any 6.x from 6.68; the EKS module needs >= 6.59
    }
  }
}
