#!/usr/bin/env python
import base64
import json
import os

import google.auth
from google.cloud.secretmanager import SecretManagerServiceClient
from google.oauth2 import service_account
from googleapiclient.discovery import build
from logzero import logger

DEFAULT_SECRET_NAME = os.getenv(
    "EVENTS_PAGE_SECRET_NAME",
    "projects/538480189659/secrets/lv-events-page/versions/latest",
)

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def read_secret(secret_name=DEFAULT_SECRET_NAME):
    credentials, project = google.auth.default()
    logger.debug(f"auth default project: {project}")
    # noqa
    client = SecretManagerServiceClient(credentials=credentials)
    response = client.access_secret_version(request={"name": secret_name})
    payload = response.payload.data.decode("UTF-8")
    secret = json.loads(payload)
    logger.debug(f"{secret.keys()=}")
    return secret


def load_credentials(scopes=DEFAULT_SCOPES):
    if os.getenv("FUNCTION_NAME") is not None:
        # Iin a GCP Cloudfunctions runtime environment we can depend on the function service account's implicit credentials
        credentials, project = google.auth.default(default_scopes=scopes)
        return credentials

    # Otherwise, assuming we are _not_ in a GCP Cloudfunctions runtime environment and thus need to pull down equivalent creds
    # to that environment's service account
    secrets = read_secret()
    service_account_info = json.loads(base64.b64decode(secrets["service_account_key"]))

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info
    )
    return credentials.with_scopes(scopes)


def build_service(service_name, version, scopes):
    return build(service_name, version, credentials=load_credentials(scopes))
