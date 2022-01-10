#!/usr/bin/env python
import os
import re
from urllib.parse import parse_qs, urlparse

from logzero import logger

from google_utils import GCLOUD_AUTH_SCOPES, build_service, read_secret

uri_regexp = re.compile(
    r"https://www.googleapis.com/drive/v3/files/(?P<file_id>[^?]+).*"
)

WEBHOOK_TOKEN = None


def parse_push(req_headers):
    push = {
        h[0].lower().lstrip("x-goog-").replace("-", "_"): h[1]
        for h in req_headers
        if h[0].lower().startswith("x-goog")
    }
    print(
        f"{push['channel_id']=} {push['message_number']=} {push.get('channel_expiration')=}"
    )
    print(f"{push['resource_id']=} {push['resource_state']=} {push['resource_uri']=}")
    print(f"{bool(push.get('channel_token') == WEBHOOK_TOKEN)=}")
    assert push.get("channel_token") == WEBHOOK_TOKEN, "channel token mismatch 💥🚨"
    return push


def ensure_token_loaded():
    global WEBHOOK_TOKEN
    if WEBHOOK_TOKEN is None:
        secret_name = os.environ["SECRET_NAME"]
        secrets = read_secret(secret_name)
        WEBHOOK_TOKEN = secrets["token"]


def process_events_push_notification(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    ensure_token_loaded()
    push = parse_push(req_headers=request.headers)

    return "idk"


def local_invocation():
    class MockRequest:
        def __init__(self, json, headers):
            self.json = json
            self._headers = headers

        def get_json(self):
            return self.json

        @property
        def headers(self):
            return self._headers

    import json

    example_headers = []
    with open(
        "examples/incoming_drive_changes_webhook.json", "r", encoding="utf-8"
    ) as f:
        example_headers = json.load(f)
    print(f"{process_events_push_notification(MockRequest({}, example_headers))}")


if __name__ == "__main__":
    local_invocation()
    breakpoint()
