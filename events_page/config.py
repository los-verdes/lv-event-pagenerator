#!/usr/bin/env python
import os


# phases of the 🌙
DEFAULT_CALENDAR_ID = "ht3jlfaac5lfd6263ulfh4tql8@group.calendar.google.com"
DEFAULT_DISPLAY_TIMEZONE = "US/Central"
DEFAULT_FOLDER_NAME = "event-cover-images"
DEFAULT_HOSTNAME = "localhost"
DEFAULT_SETTINGS_FILE_NAME = "event_page_settings.yaml"
# DEFAULT_WATCH_EXPIRATION_IN_DAYS = 1
DEFAULT_WATCH_EXPIRATION_IN_DAYS = 0.1


class Config(object):
    defaults = dict(
        calendar_id=DEFAULT_CALENDAR_ID,
        display_timezone=DEFAULT_DISPLAY_TIMEZONE,
        folder_name=DEFAULT_FOLDER_NAME,
        settings_file_name=DEFAULT_SETTINGS_FILE_NAME,
        hostname=DEFAULT_HOSTNAME,
        watch_expiration_in_days=DEFAULT_WATCH_EXPIRATION_IN_DAYS,
    )

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default

    def __getattr__(self, key):
        environ_key = f"EVENTS_PAGE_{key.upper()}"
        if environ_value := os.getenv(environ_key):
            return environ_value
        if environ_value := self.defaults.get(key):
            return environ_value

        raise AttributeError


env = Config()


# class Singleton(type):
#     _instances = {}

#     def __call__(cls, *args, **kwargs):
#         if cls not in cls._instances:
#             cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
#         return cls._instances[cls]


# class EnvConfig(metaclass=Singleton):
#     def __getattr__(self, key):
#         environ_key = f"EVENTS_PAGE_{key.upper()}"
#         if environ_value := os.getenv(environ_key):
#             return environ_value

#         return self.defaults.get(key)
