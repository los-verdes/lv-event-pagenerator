resource "random_password" "webhook_token" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "events_page" {
  secret_id = "events-page"

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "events_page" {
  secret = google_secret_manager_secret.events_page.id
  secret_data = jsonencode({
    cloudflare_api_token      = var.cloudflare_api_token
    site_publisher_gh_app_key = var.site_publisher_gh_app_key
    webhook_token             = random_password.webhook_token.result
    config                    = jsonencode(local.application_config)
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
      # TODO: ideally we'll pass config outside this secret and drop this access later...
      # "serviceAccount:${google_service_account.test_site_publisher.email}",
    ]
  }
}
