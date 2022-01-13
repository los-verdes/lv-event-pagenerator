module "github_oidc" {
  source      = "terraform-google-modules/github-actions-runners/google//modules/gh-oidc"
  version     = "~> 2.0"
  project_id  = var.gcp_project_id
  pool_id     = var.static_site_subdomain
  provider_id = "${var.static_site_subdomain}-provider"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "google.subject == 'repo:${var.github_repo}:environment:production'"
  sa_mapping = {
    "events-page-service-account" = {
      sa_name   = google_service_account.event_page.name
      attribute = "attribute.repository/${var.github_repo}"
    }
  }
}
# Service Account used to deploy this module has the following roles

# roles/iam.workloadIdentityPoolAdmin
# roles/iam.serviceAccountAdmin
