#!/usr/bin/env python
import os
from google.auth import impersonated_credentials
import google.auth
from googleapiclient.discovery import build

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/cloud-platform",
]
BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def load_credentials(scopes=DEFAULT_SCOPES):
    credentials, project = google.auth.default(scopes=scopes)
    if not credentials.has_scopes(scopes):
        source_credentials = credentials
        target_principal = (
            "gh-publisher-los-verdes-events@losverdesatx-events.iam.gserviceaccount.com"
        )
        credentials = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=target_principal,
            target_scopes=scopes,
            lifetime=500,
        )
    return credentials


def build_service(service_name, version, scopes):
    return build(service_name, version, credentials=load_credentials(scopes))
