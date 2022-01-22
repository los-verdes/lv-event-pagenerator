#!/usr/bin/env python
import json
import os
import re

import hcl
from logzero import logger

from apis import load_credentials
from apis.constants import CalendarColors

# phases of the 🌙
DEFAULT_CALENDAR_ID = "information@losverdesatx.org"
DEFAULT_DISPLAY_TIMEZONE = "US/Central"
DEFAULT_FOLDER_NAME = "calendar-event-images"
DEFAULT_GITHUB_REPO = "los-verdes/lv-event-pagenerator"
DEFAULT_HOSTNAME = "localhost"
DEFAULT_PURGE_DELAY_SECS = 30
DEFAULT_WATCH_EXPIRATION_IN_DAYS = 7


class Config(object):
    key_re = re.compile(r"^EVENTS_PAGE_(?P<key>.*)")

    github_repo = DEFAULT_GITHUB_REPO
    display_timezone = DEFAULT_DISPLAY_TIMEZONE
    overrides = dict()
    defaults = dict(
        calendar_id=DEFAULT_CALENDAR_ID,
        display_timezone=DEFAULT_DISPLAY_TIMEZONE,
        gcs_bucket_prefix="",
        hostname=DEFAULT_HOSTNAME,
        purge_delay_secs=DEFAULT_PURGE_DELAY_SECS,
        watch_expiration_in_days=DEFAULT_WATCH_EXPIRATION_IN_DAYS,
    )
    _secretsmanager_config = dict()

    @property
    def hostname(self):
        return self.static_site_hostname

    @property
    def build_workflow_filename(self):
        return "build_and_publish_site.yml"

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
        if tfvars_path := os.getenv("EVENTS_PAGE_LOAD_LOCAL_TF_VARS"):
            with open(tfvars_path) as f:
                tfvars = hcl.load(f)
                if not isinstance(tfvars, dict):
                    raise Exception(
                        f"Unable to use {tfvars=} in Config defaults; not a map..."
                    )
                logger.info(
                    f"Config after overrides loaded from {tfvars_path=}: {cfg.to_dict()=}"
                )
                cfg.overrides.update(tfvars)

    def __getattr__(self, key):
        if key in self.overrides:
            return self.overrides[key]
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
