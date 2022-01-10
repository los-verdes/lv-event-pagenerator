#!/usr/bin/env python
import base64
import json
import logging
import os
import time
from datetime import datetime

import logzero
from google.oauth2 import service_account
from googleapiclient.discovery import build
from logzero import logger

from google_utils import read_secret

# Based on: https://medium.com/swlh/google-drive-push-notification-b62e2e2b3df4

# setting up scope for
GCLOUD_AUTH_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    # "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_WEB_HOOK_ADDRESS = "https://us-central1-losverdesatx-events.cloudfunctions.net/drive-notification-receiver"
DEFAULT_SETTINGS_FILE_ID = "1jJjp94KgQ7NtI0ds5SzpNKG3s2Y96dO8"
DEFAULT_CALENDAR_ID = os.getenv("CALENDAR_ID", "information@losverdesatx.org")


def ensure_events_watch(
    service, calendar_id, channel_id, web_hook_address, token, expiration=None
):
    logger.debug(
        f"Ensure GCal events watch ({expiration=}) ({calendar_id=}) changes is in-place now..."
    )
    request = service.events().watch(
        calendarId=calendar_id,
        maxResults=2500,
        orderBy="startTime",
        singleEvents=True,
        # syncToken=,
        body=dict(
            kind="api#channel",
            type="web_hook",
            id=channel_id,
            address=web_hook_address,
            token=token,
            expiration=expiration,
        ),
    )
    response = request.execute()

    logger.debug(f"{response=}")

    resp_expiration_dt = datetime.fromtimestamp(int(response["expiration"]) // 1000)
    logger.debug(
        f"Watch (id: {response['id']}) created! Expires: {resp_expiration_dt.strftime('%x %X')}"
    )

    return response


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="Add watch for some gdrive folder.")
    parser.add_argument(
        "-q",
        "--quiet",
        help="modify output verbosity",
        action="store_true",
    )
    parser.add_argument(
        "-a",
        "--web-hook-address",
        help="HTTPS address to send push notifications to",
        default=DEFAULT_WEB_HOOK_ADDRESS,
    )
    parser.add_argument(
        "-i",
        "--channel_id",
        help="ID of the channel/ watch",
        # default=DEFAULT_SETTINGS_FILE_ID,
        default="lv-events-page-events-changes",
    )
    parser.add_argument(
        "-c",
        "--calendar_id",
        help="ID of the calendar to watch",
        default=DEFAULT_CALENDAR_ID,
    )
    parser.add_argument(
        "-e",
        "--expiration-in-days",
        help="How long until the watch expires. Defaults to None (no experation).",
        type=int,
        default=None,
    )
    args = parser.parse_args()

    if args.quiet:
        logzero.loglevel(logging.INFO)

    expiration = None
    if days := args.expiration_in_days:
        # exp_dt = datetime.utcnow() + timedelta(days=int(args.expiration_in_days))
        current_seconds = time.time()
        added_seconds = days * 24 * 60 * 60
        expiration_seconds = current_seconds + added_seconds
        expiration = round(expiration_seconds * 1000)

    event_page_secret_name = (
        "projects/538480189659/secrets/lv-events-page/versions/latest"
    )
    secrets = read_secret(event_page_secret_name)
    service_account_info = json.loads(base64.b64decode(secrets["service_account_key"]))
    sa_credentials = service_account.Credentials.from_service_account_info(
        service_account_info
    )
    # breakpoint()
    # token_secret_name = "projects/538480189659/secrets/webhook-token/versions/latest"
    # token = read_secret(client, token_secret_name)
    token = secrets["token"]

    channel_id = args.channel_id  # str(uuid.uuid4())
    logger.debug(f"Using {channel_id=}...")
    calendar_service = build("calendar", "v3", credentials=sa_credentials)
    logger.debug(f"Ensure GDrive watch ({expiration=}) for changes is in-place now...")
    response = ensure_events_watch(
        service=calendar_service,
        calendar_id=args.calendar_id,
        channel_id=channel_id,
        web_hook_address=args.web_hook_address,
        token=token,
        expiration=expiration,
    )

    # channels = [
    #     dict(id="lv-events-page-drive-changes", resource_id="hWpl0OlfRWVAbo8DFtMBa_f0hUM"),
    # ]
    # for channel in channels:
    #     print(
    #         drive_service.channels()
    #         .stop(body=dict(id=channel["id"], resourceId=channel["resource_id"]))
    #         .execute()
    #     )

    breakpoint()
