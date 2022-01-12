
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.5"
    }
    # google-beta = {
    #   source  = "hashicorp/google-beta"
    #   version = "~> 4.5"
    # }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 3.6"
    }
  }
}

# terraform {
#   backend "gcs" {
#     bucket = "PROJECT_ID-tfstate"
#     prefix = "env/dev"
#   }
# }

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

resource "google_service_account" "event_page" {
  account_id   = var.service_account_id
  display_name = var.service_account_description
}

resource "google_sourcerepo_repository" "events_page" {
  name = "github_jeffwecan_lv-event-pagenerator"
}

# resource "google_artifact_registry_repository" "static_site_builder" {
#   provider = google-beta

#   location      = var.gcp_region
#   repository_id = "events-page"
#   description   = "Builds event page static site"
#   format        = "DOCKER"
# }
