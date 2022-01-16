#!/usr/bin/env python
from apis import Singleton


class CalendarColors(metaclass=Singleton):
    _event_colors = {
        "unset": {"background": None, "id": "0"},
        "banana": {"background": "#f6c026", "id": "5"},
        "sage": {"background": "#0b8043", "id": "10"},
        "blueberry": {"background": "#3f51b5", "id": "9"},
        "flamingo": {"background": "#e67c73", "id": "4"},
        "grape": {"background": "#8e24aa", "id": "3"},
        "graphite": {"background": "#616161", "id": "8"},
        "lavender": {"background": "#a4bdfc", "id": "1"},
        "peacock": {"background": "#039be5", "id": "7"},
        "basil": {"background": "#33b679", "id": "2"},
        "tangerine": {"background": "#f5511d", "id": "6"},
        "tomato": {"background": "#d60000", "id": "11"},
    }

    @classmethod
    def get_id_by_name(cls, name):
        for n, color in cls._event_colors.items():
            if name.lower() == n:
                return color["id"]

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default

    def __getattr__(self, color_name):
        color_name = color_name.lower()
        return self._event_colors.get(color_name)
