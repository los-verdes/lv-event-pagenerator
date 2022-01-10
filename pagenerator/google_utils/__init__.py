#!/usr/bin/env python
import io
import json
import os

import google.auth
import yaml
from google.auth.transport.requests import Request
from google.cloud.secretmanager import SecretManagerServiceClient
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger


GCLOUD_AUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]
BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def load_settings_from_drive(file_id):
    drive = build_service(
        service_name="drive",
        version="v3",
        scopes=GCLOUD_AUTH_SCOPES,
    )
    file_resp = drive.files().get(fileId=file_id)
    logger.debug(f"{file_resp=}")
    print(f"{file_resp=}")
    settings_fd = get_file_id(
        drive=drive,
        file_id=file_id,
    )
    settings_fd.seek(0)
    settings = yaml.load(settings_fd, Loader=yaml.Loader)
    print(f"{settings=}")
    return settings


def read_secret(secret_name):
    credentials, project = google.auth.default()
    logger.debug(f"auth default project: {project}")
    client = SecretManagerServiceClient(credentials=credentials)
    response = client.access_secret_version(request={"name": secret_name})
    payload = response.payload.data.decode("UTF-8")
    logger.debug(f"{payload=}")
    return json.loads(payload)


def load_local_creds(scopes):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def build_service(service_name, version, scopes):
    if os.getenv("PAGENERATOR_USE_OAUTH_CREDS"):
        credentials = load_local_creds(scopes)
    else:
        credentials, project = google.auth.default(scopes)

    return build(service_name, version, credentials=credentials)


def get_file_id(drive, file_id):
    request = drive.files().get_media(fileId=file_id)
    fd = io.BytesIO()
    downloader = MediaIoBaseDownload(fd, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print("Download %d%%." % int(status.progress() * 100))

    return fd


def get_attachment(drive, attachment):
    attachment_local_path = os.path.join(BASE_DIR, "static", attachment["title"])
    if os.path.exists(attachment_local_path):
        with open(attachment_local_path, "rb") as fh:
            return fh.read()

    try:
        fh = get_file_id(drive=drive, file_id=attachment["fileId"])
        with open(attachment_local_path, "wb") as f:
            f.write(fh.getbuffer())
    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        logger.exception(f"An error occurred: {error}")