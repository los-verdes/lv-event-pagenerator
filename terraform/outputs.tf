output "github_oidc" {
  value = module.github_oidc
}

output "token" {
  sensitive = true
  value     = random_password.webhook_token.result
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

output "event_page_cdn_secret_id" {
  value = google_secret_manager_secret.events_page["events-page-cdn-token"].id
}

output "event_page_github_pat_secret_id" {
  value = google_secret_manager_secret.events_page["events-page-github-pat"].id
}

output "event_page_webhook_token_secret_name" {
  value = google_secret_manager_secret_version.events_page_webhook_token.name
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

output "source_calendar_id" {
  value = var.source_calendar_id
}

output "cdn_zone_name" {
  value = var.static_site_domain
}

output "webhook_url" {
  value = local.webhook_url
}

output "events_page_env" {
  value = local.events_page_env
}
