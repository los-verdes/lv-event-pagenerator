#!/usr/bin/env python
import requests
from logzero import logger
from apis.secrets import get_webhook_token

if __name__ == "__main__":
    import cli
    from config import cfg

    cfg.load()
    parser = cli.build_parser()
    args = cli.parse_args(parser)
    parser.add_argument(
        "-w",
        "--webhook-url",
        default=cfg.webhook_url,
        help="The GCS bucket prefix to publish the static site under.",
    )
    args = cli.parse_args(parser)

    test_push_notification = {
        "channel_expiration": "Tue, 01 Feb 2022 09:48:24 GMT",
        "channel_id": "events-page-information-watch",
        "channel_token": get_webhook_token(),
        "message_number": "11414032",
        "resource_id": "ID",
        "resource_state": "exists",
        "resource_uri": "https://www.googleapis.com/calendar/v3/calendars/information%40losverdesatx.org/events?alt=json&maxResults=2500&orderBy=startTime&singleEvents=true",
    }
    request_headers = {f"x-goog-{k}": v for k, v in test_push_notification.items()}
    webhook_resp = requests.post(
        url=args.webhook_url,
        headers=request_headers,
    )
    logger.debug(f"{webhook_resp=}")
    logger.debug(f"{webhook_resp.text=}")
