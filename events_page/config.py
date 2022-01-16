#!/usr/bin/env python
import json
import os
import re
from apis.constants import CalendarColors
from logzero import logger

from apis import load_credentials

# phases of the 🌙
DEFAULT_CALENDAR_ID = "ht3jlfaac5lfd6263ulfh4tql8@group.calendar.google.com"
DEFAULT_DISPLAY_TIMEZONE = "US/Central"
DEFAULT_FOLDER_NAME = "calendar-event-images"
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
        gdrive_folder_name=DEFAULT_FOLDER_NAME,
        gcs_bucket_prefix="",
        hostname=DEFAULT_HOSTNAME,
        purge_delay_secs=DEFAULT_PURGE_DELAY_SECS,
        gdrive_settings_file_name=DEFAULT_SETTINGS_FILE_NAME,
        watch_expiration_in_days=DEFAULT_WATCH_EXPIRATION_IN_DAYS,
    )
    _secretsmanager_config = dict()

    @property
    def hostname(self):
        return self.static_site_hostname

    @property
    def event_categories(self):
        event_categories = self.get("event_categories", "")
        if isinstance(event_categories, str):
            event_categories = json.loads(event_categories)

        if isinstance(event_categories, dict):
            for name, event_category in event_categories.items():
                event_category["category_name"] = name
                event_categories[name]["gcal_color"] = CalendarColors().get(
                    event_category["gcal_color_name"]
                )
        return event_categories

    def get(self, key, default=None):
        try:
            return self.__getattr__(key)
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
        if key in self.defaults:
            return self.defaults[key]

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
