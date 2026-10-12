variable "region" {
  description = "AWS region to create the cluster in."
  type        = string
  default     = "us-east-1"
}

variable "owner" {
  description = "Your name or handle, written into the Owner tag on every resource."
  type        = string
}

variable "cluster_name" {
  description = "EKS cluster name (also used to name the VPC)."
  type        = string
  default     = "fullsend"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}$", var.cluster_name))
    error_message = "Use 2-31 lowercase letters, digits or hyphens, starting with a letter."
  }
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version. 1.37 is in standard support (AWS EKS docs, checked 2026-10-12)."
  type        = string
  default     = "1.37"
}

variable "node_instance_types" {
  description = "EC2 instance types for the managed node group."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_count" {
  description = "Desired number of worker nodes."
  type        = number
  default     = 2

  validation {
    condition     = var.node_count >= 1 && var.node_count <= 5
    error_message = "Keep the lab cluster between 1 and 5 nodes."
  }
}
