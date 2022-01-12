output "event_page_key" {
  sensitive = true
  value     = google_service_account_key.event_page.private_key
}

output "token" {
  sensitive = true
  value     = random_password.token.result
}

output "project_number" {
  value = google_project.events_page.number
}

output "service_account_email" {
  value = google_service_account.event_page.email
}

output "secret_version_name" {
  value = google_secret_manager_secret_version.event_page_key.name
}

output "static_site_bucket_name" {
  value = google_storage_bucket.static_site.name
}

output "static_site_bucket_url" {
  value = google_storage_bucket.static_site.url
}

output "static_site_fqdn" {
  value = cloudflare_record.static_site.hostname
}