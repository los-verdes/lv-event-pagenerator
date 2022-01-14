#!/usr/bin/env python
import os


# phases of the 🌙
DEFAULT_CALENDAR_ID = "ht3jlfaac5lfd6263ulfh4tql8@group.calendar.google.com"
DEFAULT_TIMEZONE = "US/Central"
DEFAULT_FOLDER_NAME = "lv-event-cover-images"
DEFAULT_SETTINGS_FILE_NAME = "event_page_settings.yaml"


class Config(object):
    defaults = dict(
        calendar_id=DEFAULT_CALENDAR_ID,
        display_timezone=DEFAULT_TIMEZONE,
        folder_name=DEFAULT_FOLDER_NAME,
        file_name=DEFAULT_SETTINGS_FILE_NAME,
    )

    def __getattr__(self, key):
        environ_key = f"EVENTS_PAGE_{key.upper()}"
        if environ_value := os.getenv(environ_key):
            return environ_value
        if environ_value := self.defaults.get(environ_key):
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
