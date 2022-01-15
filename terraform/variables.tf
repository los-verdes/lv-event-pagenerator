variable "cloudflare_api_token" {
  sensitive = true
}

variable "cloudflare_zone" {
}

variable "github_app_id" {}

variable "github_install_id" {}

variable "site_publisher_gh_app_key" {
  sensitive = true
}

# variable "gcp_billing_account_name" {}

variable "gcp_billing_account_id" {
}

variable "gcp_project_name" {
}

variable "gcp_project_id" {
}

variable "gcp_project_owners" {
  type    = list(string)
  default = []
}

variable "gcp_project_editors" {
  type    = list(string)
  default = []
}

variable "gcp_region" {
}

variable "gdrive_folder_name" {
}

variable "gdrive_settings_file_name" {
}

variable "page_description" {
  default = ""
}
variable "static_site_hostname" {
}

variable "calendar_id" {
}

variable "github_repo" {
}
