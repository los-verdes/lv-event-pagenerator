
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.5"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 3.6"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_service_account" "event_page" {
  account_id   = var.service_account_id
  display_name = var.service_account_description
}
