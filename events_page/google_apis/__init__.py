#!/usr/bin/env python
import google.auth
from config import env
from google.auth import impersonated_credentials
from googleapiclient.discovery import build

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/cloud-platform",
]


def load_credentials(scopes=DEFAULT_SCOPES):
    credentials, _ = google.auth.default(scopes=scopes)
    if env.sa_email:
        source_credentials = credentials
        target_principal = env.sa_email
        credentials = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=target_principal,
            target_scopes=scopes,
            lifetime=500,
        )
    return credentials


def build_service(service_name, version, scopes):
    return build(service_name, version, credentials=load_credentials(scopes))
