resource "google_project" "events_page" {
  name            = var.gcp_project_name
  project_id      = var.gcp_project_id
  billing_account = var.gcp_billing_account_id
}

resource "google_project_service" "events_page" {
  for_each = toset([
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
  ])
  service                    = each.value
  disable_dependent_services = true

  timeouts {
    create = "30m"
    update = "40m"
  }
}

resource "google_project_iam_member" "project_owners" {
  for_each = toset(var.gcp_project_owners)
  project  = google_project.events_page.id
  role     = "roles/owner"
  member   = "user:${each.value}"
}

resource "google_project_iam_member" "project_editors" {
  for_each = toset(var.gcp_project_editors)
  project  = google_project.events_page.id
  role     = "roles/editor"
  member   = "user:${each.value}"
}

resource "google_project_iam_member" "allow_sa_impersonation" {
  for_each = toset(concat(var.gcp_project_owners, var.gcp_project_editors))
  project  = google_project.events_page.id
  role     = "roles/iam.serviceAccountTokenCreator"
  member   = "user:${each.value}"
}

resource "google_service_account_iam_binding" "allow_sa_impersonation" {
  service_account_id = google_service_account.site_publisher.name
  role               = "roles/iam.serviceAccountUser"
  members            = [for u in concat(var.gcp_project_owners, var.gcp_project_editors) : "user:${u}"]
}
