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
