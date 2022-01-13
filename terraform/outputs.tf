output "github_oidc" {
  value = module.github_oidc
}

output "token" {
  sensitive = true
  value     = random_password.token.result
}

output "project_number" {
  value = google_project.events_page.number
}

output "webhook_function_sa_email" {
  value = google_service_account.webhook_function.email
}

output "site_publisher_sa_email" {
  value = google_service_account.site_publisher.email
}

output "gh_terraform_applier_sa_email" {
  value = google_service_account.gh_terraform_applier.email
}

output "cdn_secret_id" {
  value = google_secret_manager_secret.event_page_cdn.id
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
  value = local.events_page_hostname
}
