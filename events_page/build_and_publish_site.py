#!/usr/bin/env python
import os
from time import sleep

import requests
from CloudFlare import CloudFlare
from flask_frozen import Freezer
from logzero import logger

from apis import calendar as gcal
from apis import drive, storage
from apis.secrets import get_cloudflare_api_token
from app import create_app
from render_templated_styles import render_templated_styles


def freeze_site(app):
    freeze_result = Freezer(app).freeze()
    logger.debug(f"{freeze_result=}")
    return freeze_result


def purge_cache(cf, cloudflare_zone):
    logger.debug(f"Loading zone info for {cloudflare_zone=}")
    zones = cf.zones.get(params={"per_page": 50, "name": cloudflare_zone})
    if not zones:
        raise Exception(
            f"Unable to find DNS zone ID for {cloudflare_zone=} at Cloudflare..."
        )
    zone = zones[0]
    zone_id = zone["id"]
    logger.debug(f"{zone_id=}")

    purge_data = {
        "purge_everything": True,
    }
    logger.info(f"Sending purge_cache request for {zone_id=} with {purge_data=}")
    purge_response = cf.zones.purge_cache.post(
        zone["id"],
        data=purge_data,
    )
    logger.debug(f"{purge_response=}")
    return purge_response


def prime_cache(site_hostname, new_paths):
    logger.info(f"Priming cache / checking responses for {len(new_paths)=}")
    responses = []
    for new_path in new_paths:
        response = requests.get(
            url=f"https://{site_hostname}{new_path}",
        )
        logger.debug(f"{response=}")
        logger.debug(f"{response.headers=}")
        response.raise_for_status()
        responses.append(response)
    return responses


def build_static_site():
    logger.info("Freezing site...")
    freeze_result = freeze_site(app=create_app())
    logger.info(f"build_static_site() => {freeze_result}")
    return freeze_result


def build_and_publish_site(
    site_hostname, cloudflare_zone, purge_delay_secs, gcs_bucket_prefix
):
    render_templated_styles(
        app=create_app(),
        gcal_service=gcal.build_service(),
        drive_service=drive.build_service(),
    )

    static_site_files = build_static_site()
    logger.debug(f"{static_site_files=}")

    storage.upload_build_to_gcs(
        client=storage.get_client(),
        bucket_id=site_hostname,
        prefix=gcs_bucket_prefix,
    )
    if cloudflare_zone is not None:
        purge_cache(
            CloudFlare(token=get_cloudflare_api_token()),
            cloudflare_zone=cloudflare_zone,
        )
        logger.info(f"Waiting for {purge_delay_secs=} before proceeding...")
        sleep(purge_delay_secs)
    else:
        logger.warning(f"Skipping cache purge bits as {cloudflare_zone} is unset...")

    logger.warning(
        '"priming" the cache may be causing more issues than it is worth, skipping for now...'
    )
    # prime_cache(site_hostname=site_hostname, new_paths=static_site_files)


if __name__ == "__main__":
    import cli
    from config import cfg

    cfg.load()
    parser = cli.build_parser()
    args = cli.parse_args(parser)
    parser.add_argument(
        "-g",
        "--gcs-bucket-prefix",
        default=cfg.gcs_bucket_prefix,
        help="The GCS bucket prefix to publish the static site under.",
    )
    parser.add_argument(
        "-s",
        "--site-hostname",
        default=cfg.hostname,
        help="Fully-qualified domain name of the published site. Used in cache purging / priming methods.",
    )
    parser.add_argument(
        "-z",
        "--cloudflare-zone",
        default=cfg.get("cloudflare_zone"),
        help="Name of zone at CDN provider (Cloudflare only provider currently considered / supported).",
    )
    parser.add_argument(
        "-p",
        "--purge-delay-secs",
        default=cfg.purge_delay_secs,
        help="How long to wait to test site response after purging cache post-publication",
    )
    args = cli.parse_args(parser)

    if os.getenv("CI"):
        output_name = "site_url"
        logger.info(
            f"In CI, setting GitHub Actions output: {output_name}={args.site_hostname}"
        )
        print("::set-output name={output_name}::{args.site_hostname}")

    build_and_publish_site(
        site_hostname=args.site_hostname,
        cloudflare_zone=args.cloudflare_zone,
        purge_delay_secs=args.purge_delay_secs,
        gcs_bucket_prefix=args.gcs_bucket_prefix,
    )

    logger.info(f"Publication of site to {args.site_hostname} completed! 🎉")
