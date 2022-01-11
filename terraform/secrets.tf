resource "time_rotating" "event_page_key" {
  rotation_days = 30
}

resource "google_service_account_key" "event_page" {
  service_account_id = google_service_account.event_page.name

  keepers = {
    rotation_time = time_rotating.event_page_key.rotation_rfc3339
  }
}

resource "random_password" "token" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "event_page_key" {
  secret_id = var.service_account_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "event_page_key" {
  secret = google_secret_manager_secret.event_page_key.id
  secret_data = jsonencode({
    service_account_key = google_service_account_key.event_page.private_key
    token               = random_password.token.result
  })
}

resource "google_secret_manager_secret_iam_policy" "policy" {
  project     = google_secret_manager_secret.event_page_key.project
  secret_id   = google_secret_manager_secret.event_page_key.secret_id
  policy_data = data.google_iam_policy.event_page_key_access.policy_data
}

data "google_iam_policy" "event_page_key_access" {
  binding {
    role = "roles/secretmanager.secretAccessor"
    members = [
      "serviceAccount:${google_service_account.event_page.email}",
    ]
  }
}
