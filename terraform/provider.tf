terraform {
  required_version = ">= 1.5.0"

  required_providers {
    launchdarkly = {
      source  = "launchdarkly/launchdarkly"
      version = "~> 2.25"
    }
  }
}

# Access token is sourced from the LAUNCHDARKLY_ACCESS_TOKEN environment
# variable (TF_VAR_launchdarkly_access_token also works). Do not hardcode.
provider "launchdarkly" {
  access_token = var.launchdarkly_access_token
}

variable "launchdarkly_access_token" {
  description = "LaunchDarkly API access token with flag + AI Config write permissions on the target project. Set via TF_VAR_launchdarkly_access_token or LAUNCHDARKLY_ACCESS_TOKEN."
  type        = string
  sensitive   = true
  default     = null
}

variable "project_key" {
  description = <<-EOT
    LaunchDarkly project key to provision resources into. REQUIRED — no default.
    This is YOUR project key, not the maintainer's. The LD project must already
    exist (this Terraform config does NOT create projects, only flags within
    them). Set via `-var project_key=...`, a `terraform.tfvars` file, or the
    `TF_VAR_project_key` environment variable.
  EOT
  type        = string

  validation {
    condition     = length(var.project_key) > 0
    error_message = "project_key must be set to your LaunchDarkly project's key."
  }
}

variable "environment_keys" {
  description = "Environment keys within the project. Used for documentation + future per-env targeting."
  type        = list(string)
  default     = ["staging", "test", "production"]
}
