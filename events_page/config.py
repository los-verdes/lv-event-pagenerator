#!/usr/bin/env python
import os

class Config(object):
    def __getattr__(self, key):
        environ_key = f"EVENTS_PAGE_{key.upper()}"
        if environ_value := os.getenv(environ_key):
            return environ_value

        return None


env = Config()
