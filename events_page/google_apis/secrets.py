#!/usr/bin/env python
import json

import google.auth
from google.cloud.secretmanager import SecretManagerServiceClient
from logzero import logger

from google_apis import Singleton


class Secrets(metaclass=Singleton):
    _secrets = None

    def __init__(self, credentials=None) -> None:
        default_credentials, project = google.auth.default()
        logger.debug(f"Default credentials project: {project}")
        self.secret_name = f"projects/{project}/secrets/events-page/versions/latest"
        logger.debug(f"Secret name: {self.secret_name=}")
        if credentials is None:
            credentials = default_credentials
        self._client = SecretManagerServiceClient(credentials=credentials)

    @property
    def secrets(self):
        if self._secrets is not None:
            return self._secrets

        response = self._client.access_secret_version(
            request={"name": self.secret_name}
        )
        payload = response.payload.data.decode("UTF-8")
        self._secrets = json.loads(payload)
        logger.debug(f"{self._secrets.keys()=}")
        return self._secrets

    def __getattr__(self, key):
        return self.secrets.get(key)


def get_cloudflare_api_token():
    cloudflare_api_token = Secrets().cloudflare_api_token
    logger.debug(f"{cloudflare_api_token=}")
    return cloudflare_api_token


def get_github_pat():
    return Secrets().site_publisher_github_pat


def get_webhook_token():
    return Secrets().webhook_token


def get_secretsmanager_config(credentials):
    if config := Secrets(credentials).config:
        return json.loads(config)
    return dict()
