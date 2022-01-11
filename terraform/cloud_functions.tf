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

# Suppose we needed this function scheduled daily or whatnot as well...
# > Notifications are not 100% reliable.
# > Expect a small percentage of messages to get dropped under normal working conditions.
# > Make sure to handle these missing messages gracefully, so that the application still
# > syncs even if no push messages are received.
# Reference: https://developers.google.com/calendar/api/guides/push#special-considerations
resource "google_cloudfunctions_function" "webhook" {
  name        = "drive-notification-receiver"
  description = "Listens for calendar-event-related drive changes"
  runtime     = "python39"

  available_memory_mb   = 128
  max_instances         = 5
  service_account_email = google_service_account.event_page.email
  source_archive_bucket = data.google_storage_bucket.cloud_functions.name
  source_archive_object = google_storage_bucket_object.webhook_archive.name
  trigger_http          = true
  entry_point           = "process_events_push_notification"

  environment_variables = {
    # EVENTS_PAGE_BASE_URL        = "https://storage.googleapis.com/${google_storage_bucket.static_site.name}/"
    EVENTS_PAGE_BASE_URL        = "https://${cloudflare_record.static_site.hostname}"
    EVENTS_PAGE_GCS_BUCKET_NAME = google_storage_bucket.static_site.name
    EVENTS_PAGE_SECRET_NAME     = google_secret_manager_secret_version.event_page_key.name
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
