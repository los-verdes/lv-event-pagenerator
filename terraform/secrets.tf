resource "random_password" "webhook_token" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "events_page" {
  for_each  = "events-page"
  secret_id = each.value

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "events_page" {
  secret = google_secret_manager_secret.events_page.id
  secret_data = jsonencode({
    cloudflare_api_key = var.cloudflare_api_key
    site_publisher_github_pat = var.site_publisher_github_pat
    webhook_token = random_password.webhook_token.result
  })
}

resource "google_secret_manager_secret_iam_policy" "events_page" {
  project     = google_secret_manager_secret.events_page.project
  secret_id   = google_secret_manager_secret.events_page.id
  policy_data = data.google_iam_policy.secrets_access.policy_data
}

data "google_iam_policy" "secrets_access" {
  binding {
    role = "roles/secretmanager.secretAccessor"
    members = [
      "serviceAccount:${google_service_account.webhook_function.email}",
      "serviceAccount:${google_service_account.site_publisher.email}",
    ]
  }
}
