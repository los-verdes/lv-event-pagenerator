#!/usr/bin/env python
import os

from logzero import logger

from app import create_app
from google_apis import cloudbuild

DEFAULT_REPO_NAME = "github_jeffwecan_lv-event-pagenerator"


def trigger_site_build():
    app = create_app()
    if static_site_bucket := app.config.get("static_site_bucket"):
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "losverdesatx-events")
        build_result = cloudbuild.trigger_build(
            client=cloudbuild.get_client(),
            project_id=project_id,
            static_site_bucket=static_site_bucket,
            repo_name=DEFAULT_REPO_NAME,
        )
        logger.debug(f"{build_result=}")
    else:
        raise Exception(
            "No static_site_bucket config key set, unable to complete site build!"
        )


if __name__ == "__main__":
    trigger_site_build()
