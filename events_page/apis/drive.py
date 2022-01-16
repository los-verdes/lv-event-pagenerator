#!/usr/bin/env python
import io
import mimetypes
import os
import re

from config import cfg
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger

from apis import load_credentials

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def build_service(credentials=None):
    if credentials is None:
        credentials = load_credentials()
    return build("drive", "v3", credentials=credentials)


def get_local_path_from_file_id(service, file_id):
    file = service.files().get(fileId=file_id).execute()
    return get_local_path_for_file(file["id"], file["mimeType"])


def get_local_path_for_file(file_id, mime_type=None):
    local_filename = f"{file_id}{mimetypes.guess_extension(mime_type)}"
    return os.path.abspath(
        os.path.join(
            BASE_DIR,
            "..",
            "static",
            local_filename,
        )
    )


def download_event_images(service, events):
    downloaded_images = {}
    image_files = [
        e.cover_image_attachment for e in events if e.cover_image_attachment is not None
    ]
    for image_file in image_files:
        download_image(service, image_file)
        downloaded_images[image_file["name"]] = os.path.basename(
            image_file["local_path"]
        )
    logger.debug(f"download_all_images_in_folder() => {image_files=}")
    return downloaded_images


def download_image(service, image_file):
    if file_id := image_file.get("fileId"):
        image_file["id"] = file_id
    image_file["local_path"] = get_local_path_for_file(
        image_file["id"], image_file["mimeType"]
    )
    if os.path.exists(image_file["local_path"]):
        logger.debug(
            f"{image_file} already present on disk! Skipping download..."
        )
        return image_file

    try:
        fh = download_file_id(service=service, file_id=image_file["id"])
        with open(image_file["local_path"], "wb") as f:
            f.write(fh.getbuffer())
    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        logger.exception(f"An error occurred: {error}")

    return image_file


def download_file_id(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fd = io.BytesIO()
    downloader = MediaIoBaseDownload(fd, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        logger.debug(f"{file_id=} download progress: {int(status.progress() * 100)}%")
    return fd


def list_files(service, q):
    # logger.debug(f"list_files(): {q=}")
    file_list_resp = (
        service.files()
        .list(
            corpora="allDrives",
            q=q,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        )
        .execute()
    )
    # logger.debug(f"list_files(): {q=} => {file_list_resp=}")
    return file_list_resp


def add_category_image_file_metadata(drive_service, event_categories):
    parsed_categories = dict()
    uri_regexp = re.compile(r"https://drive.google.com/file/d/(?P<file_id>[^?]+)/.*")
    for name, event_category in event_categories.items():
        default_cover_image = event_category.get("default_cover_image", "")
        if default_cover_image is not None and uri_regexp.match(default_cover_image):
            if cover_image_uri_matches := uri_regexp.match(default_cover_image):
                cover_image_file_id = cover_image_uri_matches.groupdict()["file_id"]
                event_category["file_metadata"] = (
                    drive_service.files().get(fileId=cover_image_file_id).execute()
                )
        parsed_categories[name] = event_category

    return parsed_categories


def download_category_images(drive_service, event_categories):
    downloaded_images = {}
    for name, event_category in event_categories.items():
        if "file_metadata" not in event_category:
            logger.debug(
                f"No file_metadata key for {name}. Assuming we have no image to download and continuing..."
            )
            continue
        image_file = download_image(
            drive_service,
            event_category["file_metadata"],
        )

        local_path = os.path.basename(image_file["local_path"])
        downloaded_images[image_file["name"]] = local_path
        event_category["cover_image_filename"] = os.path.join(
            str(cfg.gcs_bucket_prefix), local_path
        )

    logger.debug(f"download_category_images() => {downloaded_images=}")
    return downloaded_images
