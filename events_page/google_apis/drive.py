#!/usr/bin/env python
import io
import mimetypes
import os
import re
import time
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger
from ruamel import yaml

from google_apis import load_credentials

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def build_service(credentials=None):
    if credentials is None:
        credentials = load_credentials()
    return build("drive", "v3", credentials=credentials)


def get_settings_file_id(service, folder_name, file_name):
    files_in_folder = list_files_in_event_page_folder(
        service=service,
        folder_name=folder_name,
    )
    settings_file_id = files_in_folder[file_name]["id"]
    return settings_file_id


def load_setting(service, key, folder_name, file_name):
    return load_settings(service, folder_name, file_name).get(key)


def load_settings(service, folder_name, file_name):
    settings_file_id = get_settings_file_id(service, folder_name, file_name)
    print(f"load_settings_from_drive(): {settings_file_id=}")
    settings_fd = download_file_id(
        service=service,
        file_id=settings_file_id,
    )
    settings_fd.seek(0)
    settings = yaml.load(settings_fd, Loader=yaml.Loader)
    # print(f"load_settings_from_drive(): {settings=}")
    return settings


def get_local_path_from_file_id(service, file_id):
    file = service.files().get(fileId=file_id).execute()
    return get_local_path_for_file(file["id"], file["mimeType"])


def get_local_path_for_file(file_id, mime_type=None):
    local_filename = f"{file_id}{mimetypes.guess_extension(mime_type)}"
    return os.path.join(
        BASE_DIR,
        "..",
        "static",
        local_filename,
    )


def download_all_images(service, folder_name):
    files_in_folder = list_files_in_event_page_folder(
        service=service,
        folder_name=folder_name,
    )
    image_files = [
        f for f in files_in_folder.values() if f["mimeType"].startswith("image/")
    ]
    print(f"download_images_from_drive(): {image_files=}")
    for image_file in image_files:
        download_image(service, image_file)
    return image_files


def download_image(service, image_file):

    image_file["local_path"] = get_local_path_for_file(
        image_file["id"], image_file["mimeType"]
    )
    if os.path.exists(image_file["local_path"]):
        logger.debug(
            f"{image_file['name']} already present on disk: {image_file['local_path']}. Skipping download..."
        )
        return image_file

    try:
        fh = download_file_id(service=service, file_id=image_file["id"])
        logger.debug(
            f"{image_file['name']} already present on disk: {image_file['local_path']}. Skipping download..."
        )
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


def get_event_page_folder(service, folder_name):
    get_parent_folder_q = (
        f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
    )
    list_resp = list_files(service, get_parent_folder_q)
    assert len(list_resp.get("files", [])) == 1
    event_page_folder = list_resp["files"][0]
    # logger.debug(f"get_event_page_folder(): {event_page_folder=}")
    return event_page_folder


def list_files_in_event_page_folder(service, folder_name):
    event_page_folder = get_event_page_folder(
        service=service,
        folder_name=folder_name,
    )
    files = list_files(
        service=service, q=f"'{event_page_folder['id']}' in parents"
    ).get("files", [])
    files_by_name = {f["name"]: f for f in files}
    logger.debug(f"list_files_in_event_page_folder(): {files_by_name=}")
    return files_by_name


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


def download_category_images(drive_service, event_categories):
    parsed_categories = dict()
    uri_regexp = re.compile(r"https://drive.google.com/file/d/(?P<file_id>[^?]+)/.*")
    for name, event_category in event_categories.items():
        default_cover_image = event_category.get("default_cover_image", "")
        if cover_image_uri_matches := uri_regexp.match(default_cover_image):
            cover_image_file_id = cover_image_uri_matches.groupdict()["file_id"]

            file = drive_service.files().get(fileId=cover_image_file_id).execute()
            image_file = download_image(
                drive_service,
                file,
            )
            event_category["cover_image_filename"] = os.path.basename(
                image_file["local_path"]
            )
        parsed_categories[name] = event_category

    return parsed_categories


def ensure_watch(
    service, channel_id, web_hook_address, webhook_token, file_id, expiration_in_days=1
):
    # exp_dt = datetime.utcnow() + timedelta(days=int(args.expiration_in_days))
    current_seconds = time.time()
    added_seconds = expiration_in_days * 24 * 60 * 60
    expiration_seconds = current_seconds + added_seconds
    expiration = round(expiration_seconds * 1000)
    drive_id = service.files().get(fileId=file_id).execute()["id"]
    logger.debug(
        f"Ensure GDrive watch ({expiration=}) ({drive_id=}) changes is in-place now..."
    )
    page_token_resp = service.changes().getStartPageToken().execute()
    logger.debug(f"{page_token_resp=}")
    request = service.changes().watch(
        pageToken=page_token_resp["startPageToken"],
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        body=dict(
            kind="api#channel",
            type="web_hook",
            token=webhook_token,
            id=channel_id,
            address=web_hook_address,
            expiration=expiration,
        ),
    )
    response = request.execute()
    resp_expiration_dt = datetime.fromtimestamp(int(response["expiration"]) // 1000)
    logger.debug(
        f"Watch (id: {response['id']}) created! Expires: {resp_expiration_dt.strftime('%x %X')}"
    )

    return response
