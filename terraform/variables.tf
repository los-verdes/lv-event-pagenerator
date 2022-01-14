variable "enabled_gcp_services" {
  type = list(string)
  default = [
    "appengine.googleapis.com",
    "calendar-json.googleapis.com",  # Google Calendar API
    "cloudapis.googleapis.com",      # Google Cloud APIs
    "cloudbuild.googleapis.com",     # Cloud Build API
    "cloudfunctions.googleapis.com", # Cloud Functions API
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "containerregistry.googleapis.com", # Container Registry API
    "drive.googleapis.com",             # Google Drive API
    "iam.googleapis.com",
    "iamcredentials.googleapis.com", # IAM Credentials API
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com", # Secret Manager API
    "sts.googleapis.com",
  ]
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

variable "page_description" {
  default = ""
}

variable "static_site_domain" {
}

variable "static_site_subdomain" {
}

variable "source_calendar_id" {
}

variable "github_repo" {
}
