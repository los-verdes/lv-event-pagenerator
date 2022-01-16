# calendar_id               = "information@losverdesatx.org"
# gcp_billing_account_name = "Los Verdes"
calendar_id            = "tnf6pf0ucprlk8hr9loas1vp74@group.calendar.google.com"
cloudflare_zone        = "asfasfsafsasfa.org"
gcp_billing_account_id = "019767-2A54C9-AE07C6"
gcp_project_editors    = []
gcp_project_id         = "losverdesatx-events"
gcp_project_name       = "Los Verdes events page!"
gcp_project_owners     = ["Jeff.hogan1@gmail.com"]
gcp_region             = "us-central1"
githubapp_id           = "164885"
githubapp_install_id   = "22283839"
github_repo            = "los-verdes/lv-event-pagenerator"
page_description       = "Los Verdes Event Page"
static_site_hostname   = "los-verdes-events.asfasfsafsasfa.org"

event_categories = {
  # Default category (what is used if no explicit color is set for the matching calendar event)
  misc = {
    gcal_color_name = "unset"

    bg_color = "#000000"
  }

  los-verdes = {
    gcal_color_name = "sage"

    always_shown_in_filters = true
    bg_color                = "#000000"
    default_cover_image     = "https://drive.google.com/file/d/1AATD3ehu6HS-q49rso0jC8P6ZoKaGsjN/view?usp=sharing"
    text_bg_color           = "#00b140"
    text_fg_color           = "#FFFFFF"
  }

  la-murga = {
    gcal_color_name = "graphite"

    always_shown_in_filters = true
    default_cover_image     = "https://drive.google.com/file/d/1abvwXtd4ipJWtidsYzwKvNjzqh-HJFGd/view?usp=sharing"
    bg_color                = "#000000"
  }

  home-games = {
    gcal_color_name = "grape"

    always_shown_in_filters = true
    bg_color                = "#00b140"
    text_bg_color           = "#000000"
    text_fg_color           = "#FFFFFF"
  }

  away-games = {
    gcal_color_name = "flamingo"

    always_shown_in_filters = true
    bg_color                = "#000000"
  }
}
