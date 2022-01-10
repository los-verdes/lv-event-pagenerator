#!/usr/bin/env python
import io
import os

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger

from google_utils import build_service, load_credentials

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

DRIVE_RO_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
DEFAULT_FOLDER_NAME = "lv-event-cover-images"


def build_drive_service():
    return build("drive", "v3", credentials=load_credentials())

def get_event_page_folder(drive, folder_name=DEFAULT_FOLDER_NAME):
    get_parent_folder_q = f"name = '{folder_name}'"
    list_resp = list_files(drive, get_parent_folder_q)
    breakpoint()



def list_files(drive, q):
    query = "sharedWithMe"
    logger.debug(f"list_files(): {q=}")
    file_list_resp = (
        drive.files()
        .list(
            corpora="allDrives",
            q=q,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        )
        .execute()
    )
    logger.debug(file_list_resp)


def get_attachment(attachment):
    attachment_local_path = os.path.join(BASE_DIR, "..", "static", attachment["title"])
    if os.path.exists(attachment_local_path):
        with open(attachment_local_path, "rb") as fh:
            return fh.read()

    try:
        service = build_service(
            service_name="drive",
            version="v3",
            scopes=[DRIVE_RO_SCOPE],
        )

        request = service.files().get_media(fileId=attachment["fileId"])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))

        with open(attachment_local_path, "wb") as f:
            f.write(fh.getbuffer())
        return fh.getbuffer()
    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        logger.exception(f"An error occurred: {error}")
