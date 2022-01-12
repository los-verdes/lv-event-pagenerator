#!/usr/bin/env python
import os

from logzero import logger

from google_apis import cloudbuild

DEFAULT_REPO_NAME = "github_jeffwecan_lv-event-pagenerator"


def trigger_site_build():
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "losverdesatx-events")
    build_result = cloudbuild.trigger_build(
        client=cloudbuild.get_client(),
        project_id=project_id,
        repo_name=DEFAULT_REPO_NAME,
    )
    logger.debug(f"{build_result=}")
    return build_result


if __name__ == "__main__":
    trigger_site_build()
