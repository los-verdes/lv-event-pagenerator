#!/usr/bin/env python
import logging

import logzero
from googleapiclient.errors import HttpError
from logzero import logger

from apis import calendar
from apis.secrets import get_webhook_token

logzero.loglevel(logging.INFO)


def ensure_watch(
    api_module,
    channel_id,
    web_hook_address,
    webhook_token,
    expiration_in_days,
    watch_kwargs=None,
):
    if watch_kwargs is None:
        watch_kwargs = dict()

    service = getattr(api_module, "build_service")()
    try:
        response = getattr(api_module, "ensure_watch")(
            service=service,
            channel_id=channel_id,
            web_hook_address=web_hook_address,
            webhook_token=webhook_token,
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


def ensure_events_watch(
    web_hook_address, webhook_token, calendar_id, expiration_in_days
):
    ensure_watch(
        api_module=calendar,
        channel_id=f"events-page-{calendar_id.split('@', 1)[0]}-watch",
        web_hook_address=web_hook_address,
        webhook_token=webhook_token,
        expiration_in_days=expiration_in_days,
        watch_kwargs=dict(
            calendar_id=calendar_id,
        ),
    )


if __name__ == "__main__":
    import logging

    import logzero

    import cli
    from config import cfg

    cfg.load()
    parser = cli.build_parser()
    args = cli.parse_args(parser)
    parser.add_argument(
        "-c",
        "--calendar-id",
        default=cfg.calendar_id,
    )
    parser.add_argument(
        "-e",
        "--expiration-in-days",
        default=cfg.watch_expiration_in_days,
    )
    parser.add_argument(
        "-w",
        "--web-hook-address",
        default=cfg.webhook_url,
    )
    args = cli.parse_args(parser)

    ensure_events_watch(
        web_hook_address=args.web_hook_address,
        webhook_token=get_webhook_token(),
        calendar_id=args.calendar_id,
        expiration_in_days=float(args.expiration_in_days),
    )
