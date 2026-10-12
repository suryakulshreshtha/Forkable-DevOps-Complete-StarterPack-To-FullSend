provider "aws" {
  region = var.region

  # Every resource gets these tags, which makes cost reports and clean-up easy.
  default_tags {
    tags = {
      Project   = "fullsend-starterpack"
      ManagedBy = "terraform"
      Owner     = var.owner
    }
  }
}
