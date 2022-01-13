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
    "gh-site-publisher" = {
      sa_name   = google_service_account.site_publisher.name
      attribute = "attribute.environment/prod-site"
    }
    "gh-terraform-applier" = {
      sa_name   = google_service_account.gh_terraform_applier.name
      attribute = "attribute.environment/prod-gcp-project"
    }
  }
}

resource "google_service_account" "site_publisher" {
  account_id   = "gh-publisher-${var.static_site_subdomain}"
  display_name = var.service_account_description
}

resource "google_project_iam_member" "site_publisher_viewer" {
  project = google_project.events_page.id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.site_publisher.email}"
}

resource "google_service_account" "gh_terraform_applier" {
  account_id   = "gh-owner-${var.static_site_subdomain}"
  display_name = "Identity used for privileged deploys within GitHub Actions workflow runs"
}

resource "google_project_iam_member" "gh_terraform_applier" {
  project = google_project.events_page.id
  role    = "roles/owner"
  member  = "serviceAccount:${google_service_account.gh_terraform_applier.email}"
}
