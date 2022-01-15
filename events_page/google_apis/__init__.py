#!/usr/bin/env python
import os

import google.auth
from google.auth import impersonated_credentials
from googleapiclient.discovery import build

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/cloud-platform",
]


def load_credentials(scopes=DEFAULT_SCOPES):
    credentials, _ = google.auth.default(scopes=scopes)
    if sa_email := os.getenv("EVENTS_PAGE_SA_EMAIL"):
        source_credentials = credentials
        target_principal = sa_email
        credentials = impersonated_credentials.Credentials(
            source_credentials=source_credentials,
            target_principal=target_principal,
            target_scopes=scopes,
            lifetime=500,
        )
    return credentials


def build_service(service_name, version, scopes):
    return build(service_name, version, credentials=load_credentials(scopes))


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        else:
            cls._instances[cls].__init__(*args, **kwargs)
        return cls._instances[cls]
