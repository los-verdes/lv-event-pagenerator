#!/usr/bin/env python
import json

import google.auth
from google.cloud.secretmanager import SecretManagerServiceClient
from logzero import logger
from config import env


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Secrets(metaclass=Singleton):
    _secrets = None

    @property
    def secrets(self):
        if self._secrets is not None:
            return self._secrets

        credentials, project = google.auth.default()
        logger.debug(f"Default credentials project: {project}")
        logger.debug(f"Retriving {env.secret_name=}")
        client = SecretManagerServiceClient(credentials=credentials)
        response = client.access_secret_version(request={"name": env.secret_name})
        payload = response.payload.data.decode("UTF-8")
        self._secret = json.loads(payload)
        logger.debug(f"{self._secret.keys()=}")
        return self._secret

    def __getattr__(self, key):
        return self.secrets.get(key)


def get_cloudflare_api_token():
    return Secrets().get_cloudflare_api_token


def get_github_pat():
    return Secrets().site_publisher_github_pat


def get_webhook_token():
    return Secrets().webhook_token
