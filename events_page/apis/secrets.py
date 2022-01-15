#!/usr/bin/env python
import json

import google.auth
from google.cloud.secretmanager import SecretManagerServiceClient
from logzero import logger
from google.api_core.exceptions import PermissionDenied
from apis import Singleton


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

        self._secrets = self.read_secret_version(secret_name=self.secret_name)
        logger.debug(f"{self._secrets.keys()=}")
        return self._secrets

    def __getattr__(self, key):
        return self.secrets.get(key)

    def read_secret_version(self, secret_name):
        try:
            response = self._client.access_secret_version(request={"name": secret_name})
        except PermissionDenied as err:
            logger.warning(f"Unable to read secret at {secret_name=}!: {err=}")
            return dict()
        payload = response.payload.data.decode("UTF-8")
        return json.loads(payload)


def get_cloudflare_api_token():
    cloudflare_api_token = Secrets().cloudflare_api_token
    logger.debug(f"{cloudflare_api_token=}")
    return cloudflare_api_token


def get_gh_app_key():
    gh_app_key = Secrets().site_publisher_gh_app_key

    if gh_app_key:
        gh_app_key = gh_app_key.split("\\n")
        gh_app_key = "\n".join(gh_app_key)

    return gh_app_key


def get_webhook_token():
    return Secrets().webhook_token


def get_secretsmanager_config(credentials):
    if config := Secrets(credentials).config:
        return json.loads(config)
    return dict()
