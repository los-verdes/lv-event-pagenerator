module "github_oidc" {
  source      = "terraform-google-modules/github-actions-runners/google//modules/gh-oidc"
  version     = "~> 2.0"
  project_id  = var.gcp_project_id
  pool_id     = var.static_site_subdomain
  provider_id = "${var.static_site_subdomain}-provider"
  attribute_mapping = {
    "google.subject"        = "assertion.sub"
    "attribute.actor"       = "assertion.actor"
    "attribute.repository"  = "assertion.repository"
    "attribute.ref"         = "assertion.ref"
    "attribute.environment" = "assertion.environment"
  }
  attribute_condition = "assertion.repository=='${var.github_repo}'"
  sa_mapping = {
    "gh-branch-main" = {
      sa_name   = google_service_account.event_page.name
      attribute = "attribute.ref/refs/heads/main"
    }
    "gh-env-production" = {
      sa_name   = google_service_account.gh_env_production.name
      attribute = "attribute.environment/production"
    }
  }
}

resource "google_service_account" "gh_env_production" {
  account_id   = "gh-env-prod-${var.service_account_id}"
  display_name = "Identity used for privileged deploys within GitHub Actions workflow runs"
}

resource "google_project_iam_member" "gh_env_production_owner" {
  project = google_project.events_page.id
  role    = "roles/owner"
  member  = "serviceAccount:${google_service_account.gh_env_production.email}"
}


# Service Account used to deploy this module has the following roles

# roles/iam.workloadIdentityPoolAdmin
# roles/iam.serviceAccountAdmin
