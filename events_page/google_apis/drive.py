#!/usr/bin/env python
import io
import mimetypes
import os
import re
import time
from datetime import datetime

from config import cfg
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger
from ruamel import yaml

from google_apis import Singleton, load_credentials

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def build_service(credentials=None):
    if credentials is None:
        credentials = load_credentials()
    return build("drive", "v3", credentials=credentials)


class DriveSettings(metaclass=Singleton):
    _settings = dict()
    _drive_service = None

    def __init__(self, drive_service=None) -> None:
        self._drive_service = drive_service
        if self._drive_service is None:
            self._drive_service = build_service()
        if not self._settings:
            self.refresh()

    def refresh(self):
        logger.warning('DriveSettings refresh!')
        self._settings = load_settings(
            self._drive_service, cfg.folder_name, cfg.settings_file_name
        )

    @property
    def settings(self):
        return self._settings

    def __getattr__(self, key):
        return self.settings.get(key)


def get_settings_file_id(service, folder_name, file_name):
    files_in_folder = list_files_in_event_page_folder(
        service=service,
        folder_name=folder_name,
    )
    if file_name not in files_in_folder:
        return None

    settings_file_id = files_in_folder[file_name]["id"]
    return settings_file_id


def load_setting(service, key, folder_name, file_name):
    return load_settings(service, folder_name, file_name).get(key)


def load_settings(service, folder_name, file_name):
    settings_file_id = get_settings_file_id(service, folder_name, file_name)
    if settings_file_id is None:
        logger.warning(
            f"Unable to find file of id of {folder_name}/{file_name}. Using default settings!"
        )
        return dict()
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


def download_all_images_in_folder(service, folder_name):
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

    logger.debug(f"download_all_images_in_folder() => {image_files=}")
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
    try:
        event_page_folder = get_event_page_folder(
            service=service,
            folder_name=folder_name,
        )

    except HttpError as err:
        if err.status_code != 404:
            raise
        logger.warning(
            f"Unable to list event page folders, no files / relying on defaults and such: {err=}"
        )
        return dict()

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


def add_category_image_file_metadata(drive_service, event_categories):
    parsed_categories = dict()
    uri_regexp = re.compile(r"https://drive.google.com/file/d/(?P<file_id>[^?]+)/.*")
    for name, event_category in event_categories.items():
        default_cover_image = event_category.get("default_cover_image", "")
        if cover_image_uri_matches := uri_regexp.match(default_cover_image):
            cover_image_file_id = cover_image_uri_matches.groupdict()["file_id"]

            event_category["file_metadata"] = (
                drive_service.files().get(fileId=cover_image_file_id).execute()
            )
        parsed_categories[name] = event_category

    return parsed_categories


def download_category_images(drive_service, event_categories):
    downloaded_images = []
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
        downloaded_images.append(local_path)
        event_category["cover_image_filename"] = local_path

    logger.debug(f"download_category_images() => {download_image=}")
    return downloaded_images


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
