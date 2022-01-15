#!/usr/bin/env python
import logging
import os
import re

import logzero
from logzero import logger

from config import cfg
from dispatch_build_workflow_run import (dispatch_build_workflow_run,
                                         get_github_client)
from google_apis.secrets import get_gh_app_key, get_webhook_token

uri_regexp = re.compile(
    r"https://www.googleapis.com/drive/v3/files/(?P<file_id>[^?]+).*"
)

logzero.loglevel(logging.INFO)


def process_push_notification(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    cfg.load()
    push = parse_push(req_headers=request.headers)
    logger.info(f"push received: {push=}")
    logger.info(f"{request.url=} {os.getenv('FUNCTION_NAME')=}")

    if push["resource_uri"].startswith("https://www.googleapis.com/calendar"):
        logger.debug("calendar push!")

    dispatched_workflow_run = dispatch_build()
    logger.debug(f"dispatch_build() result: {dispatched_workflow_run=}")
    return f"{dispatched_workflow_run.id=}: {dispatched_workflow_run.status=}"


def dispatch_build():
    github_org, repo_name = cfg.github_repo.split("/", 1)
    github_client = get_github_client(
        owner=github_org,
        repo=repo_name,
        app_id=int(cfg.githubapp_id),
        app_key=get_gh_app_key(),
        install_id=int(cfg.githubapp_install_id),
    )

    workflow_run = dispatch_build_workflow_run(
        github_client=github_client,
        github_ref="main",
        workflow_filename="trigger_site_build.yml",
    )
    return workflow_run


def parse_push(req_headers):
    webhook_token = get_webhook_token()
    push = {
        h[0].lower().lstrip("x-goog-").replace("-", "_"): h[1]
        for h in req_headers
        if h[0].lower().startswith("x-goog")
    }
    logger.debug(
        f"{push['channel_id']=} {push['message_number']=} {push.get('channel_expiration')=}"
    )
    logger.debug(
        f"{push['resource_id']=} {push['resource_state']=} {push['resource_uri']=}"
    )
    logger.debug(f"{bool(push.get('channel_token') == webhook_token)=}")
    assert push.get("channel_token") == webhook_token, "channel token mismatch 💥🚨"
    return push


def local_invocation():
    class MockRequest:
        def __init__(self, json, headers):
            self.json = json
            self._headers = headers
            self.url = "hi"

        def get_json(self):
            return self.json

        @property
        def headers(self):
            return self._headers

    logzero.loglevel(logging.DEBUG)
    import json

    example_headers = []
    with open(
        "examples/event_changes_webhook_headers.json", "r", encoding="utf-8"
    ) as f:
        example_headers = json.load(f)
    logger.debug(f"{process_push_notification(MockRequest({}, example_headers))}")


if __name__ == "__main__":
    local_invocation()
    # breakpoint()
