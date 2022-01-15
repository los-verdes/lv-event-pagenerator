#!/usr/bin/env python
from google.cloud import storage
import glob
import os
from logzero import logger

from google_apis import load_credentials

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def get_client(credentials=None):
    if credentials is None:
        credentials = load_credentials(credentials)
    return storage.Client()


def upload_build_to_gcs(client, bucket_id, subpath=""):
    bucket = client.get_bucket(bucket_id)
    build_dir_path = os.path.abspath(os.path.join(BASE_DIR, "..", "build/"))
    logger.info(f"Uploading {build_dir_path=} to {bucket=} ({subpath=})")
    upload_local_directory_to_gcs(client, build_dir_path, bucket, subpath)
    logger.info(f"{build_dir_path=} upload to {bucket=} ({subpath=}) completed!")


def upload_local_directory_to_gcs(client, local_path, bucket, gcs_path):
    assert os.path.isdir(local_path)
    for local_file in glob.glob(local_path + "/**"):
        if not os.path.isfile(local_file):
            # if not gcs_path:
            #     gcs_path = os.path.basename(local_file)
            # else:
            #     gcs_path = gcs_path + "/" + os.path.basename(local_file)

            upload_local_directory_to_gcs(
                client,
                local_file,
                bucket,
                os.path.join(gcs_path, os.path.basename(local_file)),
            )
        else:
            remote_path = os.path.join(gcs_path, os.path.basename(local_file))
            blob = bucket.blob(remote_path)
            logger.debug(f"Uploading {local_file=}) to {remote_path=}")
            # logger.debug(f"Uploading {blob=} ({local_file=}) to: {bucket=}")
            blob.upload_from_filename(local_file)
