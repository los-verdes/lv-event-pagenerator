resource "google_project" "events_page" {
  name            = var.gcp_project_name
  project_id      = var.gcp_project_id
  billing_account = var.gcp_billing_account_id
}

resource "google_project_service" "events_page" {
  for_each = toset(var.enabled_gcp_services)
  service                    = each.value
  disable_dependent_services = true

  timeouts {
    create = "30m"
    update = "40m"
  }
}

resource "google_project_iam_member" "project_owners" {
  for_each = toset(var.gcp_project_owners)
  project = google_project.events_page.id
  role    = "roles/owner"
  member  = "serviceAccount:${google_service_account.gh_terraform_applier.email}"
}

resource "google_project_iam_member" "project_editors" {
  for_each = toset(var.gcp_project_editors)
  project = google_project.events_page.id
  role    = "roles/owner"
  member  = "serviceAccount:${google_service_account.gh_terraform_applier.email}"
}
