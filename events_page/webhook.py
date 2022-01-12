#!/usr/bin/env python
import logging
import os
import re

from googleapiclient.errors import HttpError
import logzero
from flask_frozen import Freezer
from logzero import logger

from app import create_app
from google_utils import drive, read_secret, storage

uri_regexp = re.compile(
    r"https://www.googleapis.com/drive/v3/files/(?P<file_id>[^?]+).*"
)

logzero.loglevel(logging.INFO)


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

    refresh_static_site()

    return "idk"


def refresh_static_site():
    app = create_app()
    logger.debug(f"{app.config['FREEZER_BASE_URL']}")
    logger.debug(f"{Freezer(app).freeze()=}")

    if static_site_bucket := app.config.get("static_site_bucket"):
        storage.upload_build_to_gcs(
            client=storage.get_client(),
            bucket_id=static_site_bucket,
        )
    else:
        raise Exception(
            "No static_site_bucket config key set, unable to complete site build!"
        )


def process_pubsub_msg(event, context):
    """Background Cloud Function to be triggered by Pub/Sub.
    Args:
         event (dict):  The dictionary with data specific to this type of
                        event. The `@type` field maps to
                         `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
                        The `data` field maps to the PubsubMessage data
                        in a base64-encoded string. The `attributes` field maps
                        to the PubsubMessage attributes if any is present.
         context (google.cloud.functions.Context): Metadata of triggering event
                        including `event_id` which maps to the PubsubMessage
                        messageId, `timestamp` which maps to the PubsubMessage
                        publishTime, `event_type` which maps to
                        `google.pubsub.topic.publish`, and `resource` which is
                        a dictionary that describes the service API endpoint
                        pubsub.googleapis.com, the triggering topic's name, and
                        the triggering event type
                        `type.googleapis.com/google.pubsub.v1.PubsubMessage`.
    Returns:
        None. The output is written to Cloud Logging.
    """
    import base64

    print(
        """This Function was triggered by messageId {} published at {} to {}
    """.format(
            context.event_id, context.timestamp, context.resource["name"]
        )
    )

    if "data" in event:
        payload = base64.b64decode(event["data"]).decode("utf-8")
        logger.debug(f"{payload=}")

    ensure_drive_watch()
    refresh_static_site()


def ensure_drive_watch():

    DEFAULT_WEB_HOOK_ADDRESS = "https://us-central1-losverdesatx-events.cloudfunctions.net/push-notification-receiver"
    web_hook_address = os.getenv("EVENTS_PAGE_WEBHOOK_URL", DEFAULT_WEB_HOOK_ADDRESS)
    drive_service = drive.build_service()
    channel_id = "events-page-settings-watch"
    try:
        drive.ensure_changes_watch(
            service=drive_service,
            channel_id=channel_id,
            web_hook_address=web_hook_address,
            file_id=drive.get_settings_file_id(drive_service),
            expiration_in_days=1,
        )
    except HttpError as err:
        logger.debug(err)
        if err.reason != f"Channel id {channel_id} not unique":
            # already have watch in place
            logger.exception(f"unexpected err: {err}")
            raise err
        logger.warning(f"ignoring err: {err}")


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
    # import json
    # example_headers = []
    # with open(
    #     "examples/event_changes_webhook_headers.json", "r", encoding="utf-8"
    # ) as f:
    #     example_headers = json.load(f)
    # logger.debug(
    #     f"{process_push_notification(MockRequest({}, example_headers))}"
    # )
    # ensure_drive_watch()


if __name__ == "__main__":
    local_invocation()
    # breakpoint()
