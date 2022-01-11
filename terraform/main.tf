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

variable "static_site_domain" {
  default = "asfasfsafsasfa.org"
}

variable "static_site_subdomain" {
  default = "los-verdes-events"
}
# variable "managed_zone" {
#   default = "events-asfasfsafsasfa-org"
# }

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "~> 4.5"
    }
    cloudflare = {
      source = "cloudflare/cloudflare"
      version = "~> 3.6"
    }
  }
}

# provider "cloudflare" {
#   # Configuration options
# }

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
#   service = "iam.googleapis.com" # secret manager, drive, cloud run, cloudfunctions? cloud DNS + compute

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
  source_dir       = "${path.module}/../events_page/"
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
  source_archive_bucket = google_storage_bucket.bucket.name
  source_archive_object = google_storage_bucket_object.archive.name
  trigger_http          = true
  entry_point           = "process_events_push_notification"

  environment_variables = {
    # EVENTS_PAGE_BASE_URL        = "https://storage.googleapis.com/${google_storage_bucket.static_site.name}/"
    EVENTS_PAGE_BASE_URL        = var.cdn_domain
    EVENTS_PAGE_GCS_BUCKET_NAME = google_storage_bucket.static_site.name
    EVENTS_PAGE_SECRET_NAME     = google_secret_manager_secret_version.event_page_key.name
  }
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

resource "random_password" "token" {
  length  = 64
  special = false
}

resource "google_secret_manager_secret" "event_page_key" {
  secret_id = var.service_account_id

  # labels = {
  #   service_account_email = google_service_account.event_page.email
  # }

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

resource "google_storage_bucket" "static_site" {
  name          = "${var.static_site_sudomain}.${var.static_site_domain}"
  location      = "US"
  force_destroy = true

  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
    # not_found_page   = "404.html"
  }
  # cors {
  #   origin          = ["http://image-store.com"]
  #   method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
  #   response_header = ["*"]
  #   max_age_seconds = 3600
  # }
}
# google_storage_bucket_access_control.static_site_public_rule
# resource "google_storage_bucket_access_control" "static_site_public_rule" {
#   bucket = google_storage_bucket.static_site.name
#   role   = "READER"
#   entity = "allUsers"
# }

# google_storage_bucket_iam_member.static_site_public_rule
# resource "google_storage_bucket_iam_member" "static_site_public_rule" {
#   bucket = google_storage_bucket.static_site.name
#   role   = "roles/storage.legacyBucketReader"
#   member = "allUsers"
# }
# resource "google_storage_bucket_iam_member" "static_site_public_rule2" {
#   bucket = google_storage_bucket.static_site.name
#   role   = "roles/storage.legacyObjectReader"
#   member = "allUsers"
# }



# resource "google_compute_backend_bucket" "cdn_backend_bucket" {
#   name        = "events-page-bucket"
#   description = "Backend bucket for serving static content through CDN"
#   bucket_name = google_storage_bucket.static_site.name
#   enable_cdn  = true
#   project     = data.google_project.project.name
# }

# resource "google_compute_url_map" "cdn_url_map" {
#   name            = "cdn-url-map"
#   description     = "CDN URL map to cdn_backend_bucket"
#   default_service = google_compute_backend_bucket.cdn_backend_bucket.self_link
#   project         = data.google_project.project.name
# }

# resource "google_compute_target_https_proxy" "cdn_https_proxy" {
#   name             = "cdn-https-proxy"
#   url_map          = google_compute_url_map.cdn_url_map.self_link
#   ssl_certificates = [google_compute_managed_ssl_certificate.cdn_certificate.self_link]
#   project          = data.google_project.project.name
# }

# resource "google_compute_managed_ssl_certificate" "cdn_certificate" {
#   project = data.google_project.project.name
#   name    = "cdn-managed-certificate"

#   managed {
#     domains = [var.cdn_domain]
#   }
# }

# resource "google_compute_global_address" "cdn_public_address" {
#   name         = "cdn-public-address"
#   ip_version   = "IPV4"
#   address_type = "EXTERNAL"
#   project      = data.google_project.project.name
# }

# # ------------------------------------------------------------------------------
# # CREATE A GLOBAL FORWARDING RULE
# # ------------------------------------------------------------------------------

# resource "google_compute_global_forwarding_rule" "cdn_global_forwarding_rule" {
#   name       = "cdn-global-forwarding-https-rule"
#   target     = google_compute_target_https_proxy.cdn_https_proxy.self_link
#   ip_address = google_compute_global_address.cdn_public_address.address
#   port_range = "443"
#   project    = data.google_project.project.name
# }

# resource "google_dns_record_set" "cdn_dns_a_record" {
#   managed_zone = var.managed_zone # Name of your managed DNS zone
#   name         = "${var.cdn_domain}."
#   type         = "A"
#   ttl          = 3600 # 1 hour
#   rrdatas      = [google_compute_global_address.cdn_public_address.address]
#   project      = data.google_project.project.name
# }

data "cloudflare_zone" "static_site" {
  name = var.static_site_domain
}

resource "cloudflare_record" "static_site" {
  zone_id = data.cloudflare_zone.static_site.id
  name    = var.static_site_subdomain
  value   = "c.storage.googleapis.com"
  type    = "CNAME"
  ttl     = 3600
}


resource "google_storage_bucket_iam_member" "all_users_viewers" {
  bucket = google_storage_bucket.static_site.name
  role   = "roles/storage.legacyObjectReader"
  member = "allUsers"
}

data "google_project" "project" {
}

output "project_number" {
  value = data.google_project.project.number
}

data "google_iam_policy" "event_page_key_access" {
  binding {
    role = "roles/secretmanager.secretAccessor"
    members = [
      "serviceAccount:${google_service_account.event_page.email}",
      # "projectOwner:${data.google_project.project.number}",
    ]
  }
}

resource "google_secret_manager_secret_iam_policy" "policy" {
  project     = google_secret_manager_secret.event_page_key.project
  secret_id   = google_secret_manager_secret.event_page_key.secret_id
  policy_data = data.google_iam_policy.event_page_key_access.policy_data
}

output "event_page_key" {
  sensitive = true
  value     = google_service_account_key.event_page.private_key
}

output "token" {
  sensitive = true
  value     = random_password.token.result
}


output "service_account_email" {
  value = google_service_account.event_page.email
}

output "secret_version_name" {
  value = google_secret_manager_secret_version.event_page_key.name
}

output "static_site_bucket_name" {
  value = google_storage_bucket.bucket.name
}


output "static_site_bucket_url" {
  value = google_storage_bucket.bucket.url
}

output "cdn_domain" {
  value = var.cdn_domain
}
