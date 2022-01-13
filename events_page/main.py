#!/usr/bin/env python
import logging
import os
import re

import logzero
from logzero import logger
from dispatch_build_workflow_run import dispatch_build_workflow_run
from google_apis import read_secret

DEFAULT_CALENDAR_ID = "information@losverdesatx.org"
DEFAULT_WEB_HOOK_ADDRESS = "https://us-central1-losverdesatx-events.cloudfunctions.net/push-notification-receiver"


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
    push = parse_push(req_headers=request.headers)
    logger.info(f"push received: {push=}")
    logger.info(f"{request.url=} {os.getenv('FUNCTION_NAME')=}")

    if push["resource_uri"].startswith("https://www.googleapis.com/calendar"):
        logger.debug("calendar push!")

    dispatch_build_workflow_run()

    return "idk"


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


def get_webhook_token():
    secret_name = os.environ["EVENTS_PAGE_SECRET_NAME"]
    secrets = read_secret(secret_name)
    return secrets["token"]


def get_base_url():
    return f"https://{os.getenv('EVENTS_PAGE_HOSTNAME')}"


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
