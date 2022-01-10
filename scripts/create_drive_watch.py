#!/usr/bin/env python
import json
import logging
import os
import time
import uuid
import base64
from datetime import datetime, timedelta
import google.auth
from google.oauth2 import service_account
import logzero
from dateutil.parser import parse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from logzero import logger

from google.cloud.secretmanager import SecretManagerServiceClient
from pagenerator.google_utils import build_service, get_file_id

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


def ensure_changes_watch(service, channel_id, web_hook_address, expiration=None):
    drive_id = service.files().get(fileId=DEFAULT_SETTINGS_FILE_ID).execute()["id"]
    logger.debug(
        f"Ensure GDrive watch ({expiration=}) ({drive_id=}) changes is in-place now..."
    )
    # logger.debug(f"{drive_id=}")
    page_token_resp = service.changes().getStartPageToken().execute()
    logger.debug(f"{page_token_resp=}")
    # breakpoint()
    request = service.changes().watch(
        pageToken=page_token_resp["startPageToken"],
        # driveId=drive_id,
        # includeItemsFromAllDrives=True,
        # supportsAllDrives=True,
        includeItemsFromAllDrives=False,
        supportsAllDrives=False,
        body=dict(
            kind="api#channel",
            type="web_hook",
            id=channel_id,
            address=web_hook_address,
            # expiration=expiration,
        ),
    )
    response = request.execute()

    logger.debug(f"{response=}")

    resp_expiration_dt = datetime.fromtimestamp(int(response["expiration"]) // 1000)
    logger.debug(
        f"Watch (id: {response['id']}) created! Expires: {resp_expiration_dt.strftime('%x %X')}"
    )

    return response


def ensure_file_watch(service, channel_id, web_hook_address, file_id, expiration=None):
    logger.debug(
        f"Ensure GDrive watch ({expiration=}) for {file_id=} is in-place now..."
    )
    request = service.files().watch(
        fileId=file_id,
        body=dict(
            kind="api#channel",
            type="web_hook",
            id=channel_id,
            address=web_hook_address,
            # expiration=expiration,
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
        default="lv-events-page-webhook",
    )
    parser.add_argument(
        "-f",
        "--file-id",
        help="ID of the GDrive file to watch",
        # default=DEFAULT_SETTINGS_FILE_ID,
        default=None,
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

    credentials, project = google.auth.default(GCLOUD_AUTH_SCOPES)
    client = SecretManagerServiceClient(credentials=credentials)

    secret_name = "projects/538480189659/secrets/event-page-key/versions/latest"
    response = client.access_secret_version(request={"name": secret_name})
    payload = response.payload.data.decode("UTF-8")
    service_account_info = json.loads(base64.b64decode(payload).decode())
    sa_credentials = service_account.Credentials.from_service_account_info(service_account_info)
    # breakpoint()

    channel_id = args.channel_id  # str(uuid.uuid4())
    logger.debug(f"Using {channel_id=}...")
    drive_service = build("drive", "v3", credentials=sa_credentials)
    if file_id := args.file_id:
        response = ensure_file_watch(
            service=drive_service,
            channel_id=channel_id,
            web_hook_address=args.web_hook_address,
            file_id=file_id,
            expiration=expiration,
        )
    else:
        logger.debug(
            f"Ensure GDrive watch ({expiration=}) for {file_id=} is in-place now..."
        )
        response = ensure_changes_watch(
            service=drive_service,
            channel_id=channel_id,
            web_hook_address=args.web_hook_address,
            expiration=expiration,
        )

    resp_output_path = f"{response['id']}.json"
    logger.info(f"Writing response data to: {resp_output_path}")
    with open(resp_output_path, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=4)

    breakpoint()
