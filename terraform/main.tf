variable "project_id" {
  default = "losverdesatx-events"
}

variable "region" {
  default = "us-central1"
}

variable "service_account_id" {
  default = "lv-events-page"
}

variable "service_account_description" {
  default = "Los Verdes Event Page"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# resource "google_project" "my_project" {
#   name       = "My Project"
#   project_id = "your-project-id"
#   org_id     = "1234567"
# }

# resource "google_project_service" "project" {
#   project = "your-project-id"
#   service = "iam.googleapis.com" # secret manager, drive, cloud run, cloudfunctions?

#   timeouts {
#     create = "30m"
#     update = "40m"
#   }

#   disable_dependent_services = true
# }

data "archive_file" "webhook_function" {
  type             = "zip"
  output_file_mode = "0666"
  output_path      = "${path.module}/webhook_function.zip"
  source_dir       = "${path.module}/../pagenerator/"
}


resource "google_storage_bucket" "bucket" {
  name     = "lv-event-page"
  location = "US"
}

resource "google_storage_bucket_object" "archive" {
  name   = "functions/webhook_${data.archive_file.webhook_function.output_sha}.zip"
  bucket = google_storage_bucket.bucket.name
  source = data.archive_file.webhook_function.output_path
}

resource "google_cloudfunctions_function" "webhook" {
  name        = "drive-notification-receiver"
  description = "Listens for calendar-event-related drive changes"
  runtime     = "python39"

  available_memory_mb   = 128
  max_instances         = 5
  source_archive_bucket = google_storage_bucket.bucket.name
  source_archive_object = google_storage_bucket_object.archive.name
  trigger_http          = true
  entry_point           = "process_drive_push_notification"

  build_environment_variables = {
    GOOGLE_FUNCTION_SOURCE = "webhook.py"
  }
}

resource "google_cloudfunctions_function_iam_member" "allow_all" {
  project        = google_cloudfunctions_function.webhook.project
  region         = google_cloudfunctions_function.webhook.region
  cloud_function = google_cloudfunctions_function.webhook.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}

resource "google_service_account" "event_page" {
  account_id   = var.service_account_id
  display_name = var.service_account_description
}

# note this requires the terraform to be run regularly
resource "time_rotating" "event_page_key" {
  rotation_days = 30
}

resource "google_service_account_key" "event_page" {
  service_account_id = google_service_account.event_page.name

  keepers = {
    rotation_time = time_rotating.event_page_key.rotation_rfc3339
  }
}

resource "google_secret_manager_secret" "event_page_key" {
  secret_id = "event-page-key"

  # labels = {
  #   service_account_email = google_service_account.event_page.email
  # }

  replication {
    automatic = true
  }
}


resource "google_secret_manager_secret_version" "event_page_key" {
  secret      = google_secret_manager_secret.event_page_key.id
  secret_data = google_service_account_key.event_page.private_key
}

output "event_page_key" {
  sensitive = true
  value     = google_service_account_key.event_page.private_key
}

output "service_account_email" {
  value = google_service_account.event_page.email
}

output "secret_version_name" {
  value = google_secret_manager_secret.event_page_key.name
}
