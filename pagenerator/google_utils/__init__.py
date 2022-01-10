#!/usr/bin/env python
import io
import json
import os

import base64
import google.auth
import yaml
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from google.cloud.secretmanager import SecretManagerServiceClient
from google.oauth2.credentials import Credentials
from pydrive2.drive import GoogleDrive
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger

from pydrive2.auth import GoogleAuth

DEFAULT_SECRET_NAME = os.getenv(
    "PAGENERATOR_SECRET_NAME",
    "projects/538480189659/secrets/lv-events-page/versions/latest",
)

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def load_settings_from_drive(file_id):
    drive = build_service(
        service_name="drive",
        version="v3",
        scopes=DEFAULT_SCOPES,
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


def read_secret(secret_name=DEFAULT_SECRET_NAME):
    credentials, project = google.auth.default()
    logger.debug(f"auth default project: {project}")
    client = SecretManagerServiceClient(credentials=credentials)
    response = client.access_secret_version(request={"name": secret_name})
    payload = response.payload.data.decode("UTF-8")
    logger.debug(f"{payload=}")
    return json.loads(payload)


def load_credentials(scopes=DEFAULT_SCOPES):
    if os.getenv("FUNCTION_NAME") is not None:
        # Iin a GCP Cloudfunctions runtime environment we can depend on the function service account's implicit credentials
        credentials, project = google.auth.default()

    # Otherwise, assuming we are _not_ in a GCP Cloudfunctions runtime environment and thus need to pull down equivalent creds
    # to that environment's service account
    secrets = read_secret()
    service_account_info = json.loads(base64.b64decode(secrets["service_account_key"]))

    class Credentials(service_account.Credentials):
        access_token_expired = False
        # @property
        # def access_token_expired(self):
        #     return False
        def authorize(self, *args, **kwargs):
            pass

    credentials = Credentials.from_service_account_info(service_account_info)
    # setattr(credentials, "access_token_expired", False)
    return credentials
    # return credentials.with_scopes(scopes)


def get_pydrive_client():
    class ServiceAccountAuth(GoogleAuth):
        def Authorize(self):
            if self.http is None:
                self.http = self._build_http()
            # self.http = self.credentials.authorize(self.http)
            self.service = build(
                "drive",
                "v2",
                http=self.http,
                cache_discovery=False,
                credentials=self.credentials,
            )

    # gauth = ServiceAccountAuth()
    gauth = GoogleAuth()
    gauth.credentials = load_credentials()
    return GoogleDrive(gauth)


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
