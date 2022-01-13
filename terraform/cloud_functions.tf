data "google_storage_bucket" "cloud_functions" {
  name = "gcf-sources-${google_project.events_page.number}-${var.gcp_region}"
}

data "archive_file" "webhook_function" {
  type             = "zip"
  output_file_mode = "0666"
  output_path      = "${path.module}/webhook_function.zip"
  source_dir       = "${path.module}/../events_page/"
}

resource "google_storage_bucket_object" "webhook_archive" {
  name   = "terraform/functions/webhook_${data.archive_file.webhook_function.output_sha}.zip"
  bucket = data.google_storage_bucket.cloud_functions.name
  source = data.archive_file.webhook_function.output_path
}


resource "google_service_account" "webhook_function" {
  account_id   = "webhook-${var.static_site_subdomain}"
  display_name = var.service_account_description
}

locals {
  function_name        = "push-webhook-receiver"
  events_page_hostname = "${var.static_site_subdomain}.${var.static_site_domain}"
}

resource "google_cloudfunctions_function" "webhook" {
  name        = local.function_name
  description = "Listens for calendar-event-related drive changes"
  runtime     = "python39"

  available_memory_mb   = 128
  max_instances         = 5
  service_account_email = google_service_account.webhook_function.email
  source_archive_bucket = data.google_storage_bucket.cloud_functions.name
  source_archive_object = google_storage_bucket_object.webhook_archive.name
  trigger_http          = true
  entry_point           = "process_push_notification"

  environment_variables = {
    EVENTS_PAGE_BASE_DOMAIN               = var.static_site_domain
    EVENTS_PAGE_HOSTNAME                  = local.events_page_hostname
    EVENTS_PAGE_GCS_BUCKET_NAME           = google_storage_bucket.static_site.name
    EVENTS_PAGE_WEBHOOK_TOKEN_SECRET_NAME = google_secret_manager_secret_version.events_page_webhook_token.name
    EVENTS_PAGE_CDN_TOKEN_SECRET_NAME     = "${google_secret_manager_secret.events_page["events-page-cdn-token"].name}/versions/latest"
    EVENTS_PAGE_GITHUB_PAT_SECRET_NAME    = "${google_secret_manager_secret.events_page["events-page-github-pat"].name}/versions/latest"
    EVENTS_PAGE_WEBHOOK_URL               = "https://${var.gcp_region}-${var.gcp_project_id}.cloudfunctions.net/${local.function_name}"
    EVENTS_PAGE_CALENDAR_ID               = var.source_calendar_id
    EVENTS_PAGE_GITHUB_REPO               = var.github_repo
  }

  build_environment_variables = {
    GOOGLE_FUNCTION_SOURCE = "webhook.py"
  }
}

resource "google_cloudfunctions_function_iam_member" "webhook_allow_all" {
  project        = google_cloudfunctions_function.webhook.project
  region         = google_cloudfunctions_function.webhook.region
  cloud_function = google_cloudfunctions_function.webhook.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}
