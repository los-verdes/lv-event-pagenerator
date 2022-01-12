#!/usr/bin/env python
import logging
import os
import time

import logzero
from googleapiclient.discovery import build
from logzero import logger

from google_utils import read_secret, load_credentials, calendar

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

    calendar_service = build("calendar", "v3", credentials=load_credentials())
    channel_id = args.channel_id  # str(uuid.uuid4())
    token = read_secret()["token"]

    logger.debug(
        f"Ensure GDrive watch ({channel_id=}, {expiration=}, token={token[0:2]}...{token[-2:0]}) for changes is in-place now..."
    )
    response = calendar.ensure_events_watch(
        service=calendar.build_service(credentials=load_credentials()),
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
