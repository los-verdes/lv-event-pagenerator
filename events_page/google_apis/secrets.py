#!/usr/bin/env python
import json
import os

import google.auth
from google.cloud.secretmanager import SecretManagerServiceClient
from logzero import logger

WEBHOOK_TOKEN_SECRET_NAME = os.getenv(
    "EVENTS_PAGE_WEBHOOK_TOKEN_SECRET_NAME",
    "projects/538480189659/secrets/events-page-webhook-token/versions/latest",
)

CDN_TOKEN_SECRET_NAME = os.getenv(
    "EVENTS_PAGE_CDN_TOKEN_SECRET_NAME",
    "projects/538480189659/secrets/events-page-cdn-token/versions/latest",
)

GITHUB_PAT_SECRET_NAME = os.getenv(
    "EVENTS_PAGE_GITHUB_PAT_SECRET_NAME",
    "projects/538480189659/secrets/events-page-github-pat/versions/latest",
)

SECRETS = {}


def read_secret(secret_name):
    global SECRETS
    if secret := SECRETS.get(secret_name):
        return secret
    credentials, project = google.auth.default()
    logger.debug(f"Default credentials project: {project}")
    logger.debug(f"Retriving {secret_name=}")
    client = SecretManagerServiceClient(credentials=credentials)
    response = client.access_secret_version(request={"name": secret_name})
    payload = response.payload.data.decode("UTF-8")
    secret = json.loads(payload)
    # logger.debug(f"{payload=} {secret=}")
    logger.debug(f"{secret.keys()=}")
    SECRETS[secret_name] = secret
    return secret
