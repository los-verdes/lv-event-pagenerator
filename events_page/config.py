#!/usr/bin/env python
import json
import os
import re

from logzero import logger

from apis import load_credentials

# phases of the 🌙
DEFAULT_CALENDAR_ID = "ht3jlfaac5lfd6263ulfh4tql8@group.calendar.google.com"
DEFAULT_DISPLAY_TIMEZONE = "US/Central"
DEFAULT_FOLDER_NAME = "event-cover-images"
DEFAULT_GITHUB_REPO = "jeffwecan/lv-event-pagenerator"
DEFAULT_HOSTNAME = "localhost"
DEFAULT_PURGE_DELAY_SECS = 30
DEFAULT_SETTINGS_FILE_NAME = "event_page_settings.yaml"
# DEFAULT_WATCH_EXPIRATION_IN_DAYS = 1
DEFAULT_WATCH_EXPIRATION_IN_DAYS = "0.1"


class Config(object):
    key_re = re.compile(r"^EVENTS_PAGE_(?P<key>.*)")

    github_repo = DEFAULT_GITHUB_REPO
    display_timezone = DEFAULT_DISPLAY_TIMEZONE

    defaults = dict(
        calendar_id=DEFAULT_CALENDAR_ID,
        display_timezone=DEFAULT_DISPLAY_TIMEZONE,
        folder_name=DEFAULT_FOLDER_NAME,
        hostname=DEFAULT_HOSTNAME,
        purge_delay_secs=DEFAULT_PURGE_DELAY_SECS,
        settings_file_name=DEFAULT_SETTINGS_FILE_NAME,
        watch_expiration_in_days=DEFAULT_WATCH_EXPIRATION_IN_DAYS,
    )
    _secretsmanager_config = dict()

    @property
    def event_categories(self):
        return json.loads(self.get("event_categories", ""))

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default

    def load(self):
        from apis.secrets import get_secretsmanager_config

        if not self._secretsmanager_config:
            self._secretsmanager_config = get_secretsmanager_config(
                credentials=load_credentials()
            )

    def __getattr__(self, key):
        environ_key = f"EVENTS_PAGE_{key.upper()}"
        if environ_value := os.getenv(environ_key):
            return environ_value
        if config_value := self._secretsmanager_config.get(key):
            return config_value
        if default_value := self.defaults.get(key):
            return default_value

        raise AttributeError(f"no {key=} anywhere for <Config ...>!")

    def to_dict(self):
        config_dict = self.defaults
        for k, v in os.environ.items():
            if key_match := self.key_re.match(k):
                friendly_key = key_match.groupdict()["key"].lower()
                config_dict[friendly_key] = v
        return config_dict


cfg = Config()
logger.debug(f"Config loaded from environment: {cfg.to_dict()=}")
