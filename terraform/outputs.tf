output "cloudflare_zone" {
  value = var.cloudflare_zone
}

output "events_page_secret_name" {
  value = google_secret_manager_secret_version.events_page.name
}

output "application_config" {
  value = local.application_config
}

output "gh_terraform_applier_sa_email" {
  value = google_service_account.gh_terraform_applier.email
}

output "github_oidc_provider_name" {
  value = module.github_oidc.provider_name
}

output "project_number" {
  value = google_project.events_page.number
}

output "site_publisher_sa_email" {
  value = google_service_account.site_publisher.email
}

output "calendar_id" {
  value = var.calendar_id
}

output "webhook_token" {
  sensitive = true
  value     = random_password.webhook_token.result
}

output "static_site_bucket_name" {
  value = google_storage_bucket.static_site.name
}

output "static_site_bucket_url" {
  value = google_storage_bucket.static_site.url
}

output "static_site_fqdn" {
  value = google_storage_bucket.static_site.name
}

output "webhook_function_sa_email" {
  value = google_service_account.webhook_function.email
}

output "webhook_url" {
  value = local.webhook_url
}
