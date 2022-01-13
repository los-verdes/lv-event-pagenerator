resource "random_password" "webhook_token" {
  length  = 64
  special = false
}

locals {
  secret_ids = [
    "events-page-webhook-token",
    # Note: these CDN and GitHub PAT secret values are populated outside of Terraform to simplify bootstrapping those secret versions
    "events-page-cdn-token",
    "events-page-github-pat"
  ]
}
resource "google_secret_manager_secret" "events_page" {
  for_each  = toset(local.secret_ids)
  secret_id = each.value

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "events_page_webhook_token" {
  secret = google_secret_manager_secret.events_page["events-page-webhook-token"].id
  secret_data = jsonencode({
    token = random_password.webhook_token.result
  })
}

resource "google_secret_manager_secret_iam_policy" "policy" {
  for_each    = google_secret_manager_secret.events_page
  project     = each.value.project
  secret_id   = each.value.id
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
