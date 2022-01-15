terraform {
  backend "gcs" {
    bucket = "losverdesatx-events-tfstate"
    prefix = "env/production"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 3.0"
    }
    cloudflare = {
      source = "cloudflare/cloudflare"
      # version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

locals {
  application_config = {
      cloudflare_zone    = var.cloudflare_zone
      calendar_id        = var.calendar_id
      folder_name        = var.gdrive_folder_name
      settings_file_name = var.gdrive_settings_file_name
      github_repo        = var.github_repo
      hostname           = google_storage_bucket.static_site.name
      webhook_url        = local.webhook_url
    }
}
