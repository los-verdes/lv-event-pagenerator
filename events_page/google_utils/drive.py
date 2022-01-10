#!/usr/bin/env python
import io
import os
import mimetypes
from ruamel import yaml
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger

from google_utils import load_credentials

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

DRIVE_RO_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DEFAULT_FOLDER_NAME = "lv-event-cover-images"
DEFAULT_SETTINGS_FILE_NAME = "event_page_settings.yaml"


def build_service(credentials=None):
    if credentials is None:
        credentials = load_credentials()
    return build("drive", "v3", credentials=credentials)


def load_settings(
    service, folder_name=DEFAULT_FOLDER_NAME, file_name=DEFAULT_SETTINGS_FILE_NAME
):
    files_in_folder = list_files_in_event_page_folder(
        service=service,
        folder_name=folder_name,
    )
    settings_file_id = files_in_folder[file_name]["id"]
    print(f"load_settings_from_drive(): {settings_file_id=}")
    settings_fd = download_file_id(
        service=service,
        file_id=settings_file_id,
    )
    settings_fd.seek(0)
    settings = yaml.load(settings_fd, Loader=yaml.Loader)
    print(f"load_settings_from_drive(): {settings=}")
    return settings


def get_local_path_for_file(file_id, mime_type):
    local_filename = f"{file_id}{mimetypes.guess_extension(mime_type)}"
    return os.path.join(
        BASE_DIR,
        "..",
        "static",
        local_filename,
    )


def download_all_images(service, folder_name=DEFAULT_FOLDER_NAME):
    files_in_folder = list_files_in_event_page_folder(
        service=service,
        folder_name=folder_name,
    )
    image_files = [
        f for f in files_in_folder.values() if f["mimeType"].startswith("image/")
    ]
    print(f"download_images_from_drive(): {image_files=}")
    for image_file in image_files:
        image_file["local_path"] = get_local_path_for_file(
            image_file["id"], image_file["mimeType"]
        )
        if os.path.exists(image_file["local_path"]):
            logger.debug(
                f"{image_file['name']} already present on disk: {image_file['local_path']}. Skipping download..."
            )
            continue

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
    return image_files


def download_file_id(service, file_id):
    request = service.files().get_media(fileId=file_id)
    fd = io.BytesIO()
    downloader = MediaIoBaseDownload(fd, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        logger.debug(f"{file_id=} download progress: {int(status.progress() * 100)}%")
    return fd


def get_event_page_folder(service, folder_name=DEFAULT_FOLDER_NAME):
    get_parent_folder_q = (
        f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
    )
    list_resp = list_files(service, get_parent_folder_q)
    assert len(list_resp.get("files", [])) == 1
    event_page_folder = list_resp["files"][0]
    logger.debug(f"get_event_page_folder(): {event_page_folder=}")
    return event_page_folder


def list_files_in_event_page_folder(service, folder_name=DEFAULT_FOLDER_NAME):
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
    logger.debug(f"list_files(): {q=}")
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
    logger.debug(f"list_files(): {q=} => {file_list_resp=}")
    return file_list_resp


# def get_attachment(service, attachment):
#     attachment_local_path = os.path.join(BASE_DIR, "..", "static", attachment["title"])
#     if os.path.exists(attachment_local_path):
#         with open(attachment_local_path, "rb") as fh:
#             return fh.read()

#     try:
#         fh = download_file_id(drive=service, file_id=attachment["fileId"])
#         with open(attachment_local_path, "wb") as f:
#             f.write(fh.getbuffer())
#         return fh.getbuffer()
#     except HttpError as error:
#         # TODO(developer) - Handle errors from drive API.
#         logger.exception(f"An error occurred: {error}")
