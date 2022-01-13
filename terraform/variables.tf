variable "enabled_gcp_services" {
  type = list(string)
  default = [
    "appengine.googleapis.com",
    "cloudscheduler.googleapis.com",
    "pubsub.googleapis.com",
    "calendar-json.googleapis.com",     # Google Calendar API
    "cloudapis.googleapis.com",         # Google Cloud APIs
    "cloudbuild.googleapis.com",        # Cloud Build API
    "cloudfunctions.googleapis.com",    # Cloud Functions API
    "containerregistry.googleapis.com", # Container Registry API
    "drive.googleapis.com",             # Google Drive API
    "secretmanager.googleapis.com",     # Secret Manager API

    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iamcredentials.googleapis.com", # IAM Credentials API
    "sts.googleapis.com",
  ]
}

variable "gcp_billing_account_name" {
  default = "Los Verdes"
}

variable "gcp_project_name" {
  default = "Los Verdes events page!"
}

variable "gcp_project_id" {
  default = "losverdesatx-events"
}

variable "gcp_region" {
  default = "us-central1"
}

variable "service_account_id" {
  default = "lv-events-page"
}

variable "service_account_description" {
  default = "Los Verdes Event Page"
}

variable "static_site_domain" {
  default = "asfasfsafsasfa.org"
}

variable "static_site_subdomain" {
  default = "los-verdes-events"
}
variable "source_calendar_id" {
  default = "information@losverdesatx.org"
}

variable "github_repo" {
  default = "jeffwecan/lv-event-pagenerator"
}
