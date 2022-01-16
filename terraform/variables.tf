variable "cloudflare_api_token" {
  sensitive = true
}

variable "cloudflare_zone" {
}


variable "event_categories" {
  type = map(
    object({
      gcal_color_name         = string
      always_shown_in_filters = optional(bool)
      bg_color                = optional(string)
      default_cover_image     = optional(string)
      text_bg_color           = optional(string)
      text_fg_color           = optional(string)
    })
  )
  description = "Map of task group specifications for the consul-terraform-sync Nomad job."
  default     = {}
  # validation {
  #   condition     = contains(["DEBUG", "INFO", "WARN"], var.event_categories)
  #   error_message = "The event_categories variable's value must be one of: DEBUG, INFO, WARN."
  # }
}

variable "githubapp_id" {}

variable "githubapp_install_id" {}

variable "site_publisher_gh_app_key" {
  sensitive = true
}

# variable "gcp_billing_account_name" {}

variable "gcp_billing_account_id" {
}

variable "gcp_project_name" {
}

variable "gcp_project_id" {
}

variable "gcp_project_owners" {
  type    = list(string)
  default = []
}

variable "gcp_project_editors" {
  type    = list(string)
  default = []
}

variable "gcp_region" {
}

variable "page_description" {
  default = ""
}

variable "static_site_hostname" {
}

variable "calendar_id" {
}

variable "github_repo" {
}
