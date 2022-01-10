#!/usr/bin/env python
import io
import os

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger

from google_utils import build_service

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

DRIVE_RO_SCOPE = "https://www.googleapis.com/auth/drive.readonly"



def list_files(drive):
    file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
    for file1 in file_list:
        print('title: %s, id: %s' % (file1['title'], file1['id']))

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
