project = "pagenerator"

app "pagenerator" {

  build {
    use "docker" {}

    registry {
      use "docker" {
        image = "gcr.io/losverdesatx-events/pagenerator"
        tag   = gitrefpretty()
      }
    }
  }

  deploy {
    use "google-cloud-run" {
      project  = "losverdesatx-events"
      location = "us-east4"

      port = 8080

      static_environment = {
        CALENDAR_ID = "information@losverdesatx.org"
        WAYPOINT_CEB_DISABLE = "true"
      }

      capacity {
        memory                     = 256
        cpu_count                  = 1
        max_requests_per_container = 10
        request_timeout            = 15
      }

      auto_scaling {
        max = 1
      }
    }
  }

  release {
    use "google-cloud-run" {}
  }

}
