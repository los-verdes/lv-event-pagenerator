#!/usr/bin/env python
import os

import requests
from CloudFlare import CloudFlare
from flask_frozen import Freezer
from logzero import logger

from app import create_app
from google_apis import CDN_SECRET_NAME, read_secret, storage


def freeze_site(app):
    freeze_result = Freezer(app).freeze()
    logger.debug(f"{freeze_result=}")
    return freeze_result


def purge_cache(cf, zone_name):
    logger.debug(f"Loading zone info for {zone_name=}")
    zones = cf.zones.get(params={"per_page": 50, "name": zone_name})
    if not zones:
        raise Exception(f"Unable to find DNS zone ID for {zone_name=} at Cloudflare...")
    zone = zones[0]
    zone_id = zone["id"]
    logger.debug(f"{zone_id}: {zone=}")

    # purge_files = [f"https://{base_hostname}{p}" for p in purge_paths]
    # logger.debug(
    #     f"Sending purge_cache request for {zone_id=} at prefixes: {purge_files=}"
    # )
    purge_data = {
        "purge_everything": True,
    }
    logger.debug(f"Sending purge_cache request for {zone_id=} with {purge_data=}")
    purge_response = cf.zones.purge_cache.post(
        zone["id"],
        data=purge_data,
    )
    logger.debug(f"{purge_response=}")
    return purge_response


def prime_cache(base_hostname, new_paths):
    responses = []
    for new_path in new_paths:
        response = requests.get(
            url=f"https://{base_hostname}{new_path}",
        )
        logger.debug(f"{response=}")
        logger.debug(f"{response.headers=}")
        response.raise_for_status()
        responses.append(response)
    return responses


def build_static_site():
    freeze_result = freeze_site(app=create_app())
    if static_site_bucket := os.getenv("EVENTS_PAGE_GCS_BUCKET_NAME"):
        storage.upload_build_to_gcs(
            client=storage.get_client(),
            bucket_id=static_site_bucket,
        )
    else:
        raise Exception(
            "No static_site_bucket config key set, unable to complete site build!"
        )
    cdn_api_token = read_secret(CDN_SECRET_NAME)["token"]
    zone_name = os.getenv("EVENTS_PAGE_BASE_DOMAIN", "asfasfsafsasfa.org")
    base_hostname = os.getenv("EVENTS_PAGE_HOSTNAME", f"events.{zone_name}")
    purge_cache(
        CloudFlare(token=cdn_api_token),
        zone_name=zone_name,
        # base_hostname=base_hostname,
        # purge_paths=freeze_result,
    )
    prime_cache(base_hostname=base_hostname, new_paths=freeze_result)


if __name__ == "__main__":
    build_static_site()
