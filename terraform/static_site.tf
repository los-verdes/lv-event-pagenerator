resource "google_storage_bucket" "static_site" {
  name          = "${var.static_site_subdomain}.${var.static_site_domain}"
  location      = "US"
  force_destroy = true

  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
  }
}

resource "google_storage_bucket_iam_member" "all_users_viewers" {
  bucket = google_storage_bucket.static_site.name
  role   = "roles/storage.legacyObjectReader"
  member = "allUsers"
}

data "cloudflare_zone" "static_site" {
  name = var.static_site_domain
}

resource "cloudflare_record" "static_site" {
  zone_id = data.cloudflare_zone.static_site.id
  name    = var.static_site_subdomain
  value   = "c.storage.googleapis.com"
  type    = "CNAME"
  ttl     = 1
  proxied = true
}
