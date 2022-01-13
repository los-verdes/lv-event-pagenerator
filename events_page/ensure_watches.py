#!/usr/bin/env python
import logging
import os

import logzero
from googleapiclient.errors import HttpError
from logzero import logger

from google_apis import calendar, drive
from webhook import get_webhook_token

DEFAULT_CALENDAR_ID = "information@losverdesatx.org"
DEFAULT_WEB_HOOK_ADDRESS = "https://us-central1-losverdesatx-events.cloudfunctions.net/push-notification-receiver"


logzero.loglevel(logging.INFO)


def ensure_watches():
    ensure_events_watch()
    ensure_drive_watch()


def ensure_watch(api_module, channel_id, watch_kwargs=None, expiration_in_days=1):
    if watch_kwargs is None:
        watch_kwargs = dict()

    service = getattr(api_module, "build_service")()
    try:
        response = getattr(api_module, "ensure_watch")(
            service=service,
            channel_id=channel_id,
            web_hook_address=os.getenv(
                "EVENTS_PAGE_WEBHOOK_URL", DEFAULT_WEB_HOOK_ADDRESS
            ),
            webhook_token=get_webhook_token(),
            expiration_in_days=expiration_in_days,
            **watch_kwargs,
        )
        logger.debug(f"ensure_watch(): {response=}")
    except HttpError as err:
        logger.debug(err)
        if err.reason != f"Channel id {channel_id} not unique":
            # already have watch in place
            logger.exception(f"unexpected err: {err}")
            raise err
        logger.warning(
            f"Watch {channel_id} already present ({err=}). Happily continuing..."
        )


def ensure_events_watch():
    calendar_id = os.getenv("EVENTS_PAGE_CALENDAR_ID", DEFAULT_CALENDAR_ID)
    ensure_watch(
        api_module=calendar,
        channel_id=f"events-page-{calendar_id.split('@', 1)[0]}-watch",
        watch_kwargs=dict(
            calendar_id=calendar_id,
        ),
    )


def ensure_drive_watch():
    settings_file_id = drive.get_settings_file_id(drive.build_service())
    ensure_watch(
        api_module=drive,
        channel_id=f"events-page-{settings_file_id}-watch",
        watch_kwargs=dict(
            file_id=settings_file_id,
        ),
    )


if __name__ == "__main__":
    import argparse
    import logging

    import logzero

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--quiet",
        help="modify output verbosity",
        action="store_true",
    )
    args = parser.parse_args()

    if args.quiet:
        logzero.loglevel(logging.INFO)

    ensure_watches()
