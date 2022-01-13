#!/usr/bin/env python
import os

import google.auth
from googleapiclient.discovery import build

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def load_credentials(scopes=DEFAULT_SCOPES):
    # Iin a GCP Cloudfunctions runtime environment we can depend on the function service account's implicit credentials
    credentials, project = google.auth.default(default_scopes=scopes)
    return credentials


def build_service(service_name, version, scopes):
    return build(service_name, version, credentials=load_credentials(scopes))
