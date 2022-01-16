locals {
  oidc_pool_id = replace(var.github_repo, "/", "-")
}

module "github_oidc" {
  source      = "terraform-google-modules/github-actions-runners/google//modules/gh-oidc"
  version     = "~> 2.0"
  project_id  = var.gcp_project_id
  pool_id     = local.oidc_pool_id
  provider_id = local.oidc_pool_id
  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.sub"              = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.ref"              = "assertion.ref"
    "attribute.environment"      = "assertion.environment"
    "attribute.workflow"         = "assertion.workflow"
    "attribute.job_workflow_ref" = "assertion.job_workflow_ref"
  }
  attribute_condition = "assertion.repository=='${var.github_repo}'"
  sa_mapping = {
    "gh-test-site-cleaner" = {
      sa_name   = google_service_account.test_site_publisher.name
      attribute = "attribute.workflow/cleanup-test-site-prefix"
    }
    "gh-test-site-publisher" = {
      sa_name   = google_service_account.test_site_publisher.name
      attribute = "attribute.workflow/pull-request-tests"
    }
    "gh-site-publisher" = {
      sa_name   = google_service_account.site_publisher.name
      attribute = "attribute.ref/refs/heads/main"
    }
    "gh-terraform-applier" = {
      sa_name   = google_service_account.gh_terraform_applier.name
      attribute = "attribute.environment/prod-gcp-project"
    }
  }
}

resource "google_service_account" "test_site_publisher" {
  account_id   = "test-site-publisher"
  display_name = var.page_description
}

resource "google_project_iam_member" "test_site_publisher_viewer" {
  project = google_project.events_page.id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.test_site_publisher.email}"
}

resource "google_service_account" "site_publisher" {
  account_id   = "site-publisher"
  display_name = var.page_description
}

resource "google_project_iam_member" "site_publisher_viewer" {
  project = google_project.events_page.id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.site_publisher.email}"
}

resource "google_service_account" "gh_terraform_applier" {
  account_id   = "gh-terraform-applier"
  display_name = "Identity used for privileged deploys within GitHub Actions workflow runs"
}

resource "google_project_iam_member" "gh_terraform_applier" {
  project = google_project.events_page.id
  role    = "roles/owner"
  member  = "serviceAccount:${google_service_account.gh_terraform_applier.email}"
}
