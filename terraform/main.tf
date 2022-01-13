
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
    # google-beta = {
    #   source  = "hashicorp/google-beta"
    #   version = "~> 4.5"
    # }
    # cloudflare = {
    #   source  = "cloudflare/cloudflare"
    #   version = "~> 3.6"
    # }
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


resource "google_project_iam_member" "event_page_viewer" {
  project = google_project.events_page.id
  role    = "roles/viewer"
  member  = "serviceAccount:${google_service_account.event_page.email}"
}

# resource "google_project_iam_member" "allow_functions_trigger_builds" {
#   project = google_project.events_page.id
#   role    = "roles/cloudbuild.builds.editor"
#   member  = "serviceAccount:${google_service_account.event_page.email}"
# }

# TODO: add variable with account owner iam member jazz here

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
