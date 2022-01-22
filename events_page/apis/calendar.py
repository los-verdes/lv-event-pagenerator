#!/usr/bin/env python
import base64
import re
import time
from datetime import datetime, timedelta
from functools import partial
from os.path import basename
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from config import cfg
from dateutil.parser import parse
from googleapiclient.discovery import build
from logzero import setup_logger

from apis import load_credentials
from apis.constants import CalendarColors
from apis.drive import get_local_path_for_file
from apis.mls import TeamColors

logger = setup_logger(name=__name__)


def load_calendar(service, calendar_id):
    calendar = Calendar(
        service=service,
        calendar_id=calendar_id,
        display_timezone=cfg.display_timezone,
        event_categories=cfg.event_categories,
    )

    # TODO: Should actually probably pull events <=24 hours ago start time so we don't drop events right after they start....
    events_time_min = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events_time_max = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
    calendar.load_events(
        time_min=events_time_min,
        time_max=events_time_max,
    )
    return calendar


def build_service(credentials=None):
    if credentials is None:
        credentials = load_credentials()
    return build("calendar", "v3", credentials=credentials)


class Event(object):
    today = datetime.today()
    zoom_url_regexp = re.compile(r"https://[a-zA-Z0-9]+\.zoom.us\/.*")
    game_regexp = re.compile(r"Austin FC (?P<vsat>vs|at) (?P<opponent>.*)")

    def __init__(
        self,
        raw_event,
        display_timezone,
        categories_by_color_id,
    ) -> None:
        self._event = raw_event
        self.display_timezone = display_timezone
        self.categories_by_color_id = categories_by_color_id
        self.mls_team_abbrs_by_name = TeamColors().team_abbrs_by_name()

        self.cover_image_attachment = None
        for attachment in self._event.get("attachments", []):
            if attachment["mimeType"].startswith("image/"):
                self.cover_image_attachment = attachment
                break

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default

    def __getattr__(self, key):
        if value := self._event.get(key):
            return value
        # convert key from snake to camel case
        components = key.split("_")
        # via: https://stackoverflow.com/a/19053800
        # We capitalize the first letter of each component except the first one
        # with the 'title' method and join them together.
        camelKey = components[0] + "".join(x.title() for x in components[1:])
        if value := self._event.get(camelKey):
            return value

        raise AttributeError(f"no {key=} in <Event raw_event... >")

    @property
    def category(self):
        # logger.debug(
        #     f"{self.summary} ===>\n{self.color_id=} => {self.categories_by_color_id.get(self.color_id)=}"
        # )
        if category := self.categories_by_color_id.get(self.color_id):
            return category

        return dict()

    @property
    def category_name(self):
        return self.category.get("category_name", "misc")

    @property
    def color_id(self):
        return self._event.get("colorId", "0")

    @property
    def start_dt(self):
        return self.parse_event_timestamp(self._event, "start")

    @property
    def end_dt(self):
        return self.parse_event_timestamp(self._event, "end")

    @property
    def in_past(self):
        return self.start_dt < self.today.replace(
            tzinfo=ZoneInfo(self.display_timezone)
        )

    @property
    def css_classes(self):
        return [
            f"category-{self.color_id}",
            self.event_specific_css_class,
        ]

    @property
    def event_specific_css_class(self):
        return f"event-{self.id}"

    @property
    def has_location(self):
        return bool(self.location)

    @property
    def location(self):
        return self._event.get("location", "")

    @property
    def has_description(self):
        return bool(self.description)

    @property
    def description(self):
        return self._event.get("description", "")

    @property
    def description_lines(self):
        return self.description.split("\n")

    @property
    def is_over_zoom(self):
        return bool(self.zoom_url_regexp.match(self.location))

    @property
    def cover_image_filename(self):
        if not self.cover_image_attachment:
            return None

        local_path = basename(
            get_local_path_for_file(
                file_id=self.cover_image_attachment["fileId"],
                mime_type=self.cover_image_attachment["mimeType"],
            )
        )
        return local_path

    @property
    def is_match(self):
        return self.game_regexp.match(self.summary) is not None

    @property
    def match_slug(self):
        if summary_match := self.game_regexp.match(self.summary):
            groups = summary_match.groupdict()
            opp_abbr = self.mls_team_abbrs_by_name.get(groups["opponent"], "-")
            if groups["vsat"] == "vs":
                return f"atxvs{opp_abbr}"
            else:
                return f"{opp_abbr}vsatx"
        return None

    def parse_event_timestamp(self, event, timestamp_key):
        parsed_dt = parse(
            event[timestamp_key].get("dateTime", event[timestamp_key].get("date"))
        )
        parsed_dt = parsed_dt.replace(tzinfo=ZoneInfo(self.display_timezone))
        return parsed_dt


class Calendar(object):
    # Lazy caching by way of class attribute:
    events = None
    events_time_min = None
    events_time_max = None
    last_refresh = None

    today = datetime.today()

    def __init__(
        self, service, calendar_id, display_timezone, event_categories
    ) -> None:
        self._service = service
        self.calendar_id = calendar_id
        self.display_timezone = display_timezone
        self.event_categories = event_categories
        self.cid = self.get_cid_from_id(self.calendar_id)
        self.categories_by_color_id = {}
        for name, event_category in event_categories.items():
            event_category["category_name"] = name
            color_id = CalendarColors.get_id_by_name(event_category["gcal_color_name"])
            self.categories_by_color_id[color_id] = event_category
        # logger.debug(f"{self.categories_by_color_id=}")

        self.default_category_names = [
            c["category_name"]
            for c in self.event_categories.values()
            if c.get("always_shown_in_filters")
        ]

    @property
    def cal_id_href(self):
        return f"https://calendar.google.com/calendar/embed?src={quote_plus(self.calendar_id)}"

    @property
    def cal_cid_href(self):
        return f"https://calendar.google.com/calendar/u/0?cid={self.cid}"

    @property
    def all_category_names(self):
        return list(
            set(self.default_category_names) | set(self.current_event_category_names)
        )

    @property
    def current_event_category_names(self):
        if self.events is None:
            return list()
        return [e.category_name for e in self.events]

    @property
    def additional_category_names(self):
        return list(
            set(self.current_event_category_names) - set(self.default_category_names)
        )

    @property
    def empty_category_names(self):
        return list(
            set(self.all_category_names) - set(self.current_event_category_names)
        )

    @staticmethod
    def get_cid_from_id(calendar_id):
        calendar_id_bytes = calendar_id.encode("utf-8")
        cid_base64 = base64.b64encode(calendar_id_bytes)
        cid = cid_base64.decode().rstrip("=")
        return cid

    def load_events(
        self,
        time_min,
        time_max,
    ):
        if self.events is not None:
            return self.events

        self.events_time_min = time_min
        self.events_time_max = time_max
        self.last_refresh = datetime.now(tz=ZoneInfo(cfg.display_timezone))
        logger.info(f"Getting the all events from {time_min} to {time_max}...")

        events_result = (
            self._service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                # maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        if not events:
            return []
        new_event = partial(
            Event,
            categories_by_color_id=self.categories_by_color_id,
            display_timezone=self.display_timezone,
        )
        self.events = [new_event(e) for e in events]
        return self.events


def ensure_watch(
    service,
    calendar_id,
    channel_id,
    web_hook_address,
    webhook_token,
    expiration_in_days=1,
):
    current_seconds = time.time()
    added_seconds = expiration_in_days * 24 * 60 * 60
    expiration_seconds = current_seconds + added_seconds
    expiration = round(expiration_seconds * 1000)
    logger.info(
        f"Ensuring GCal events watch for {calendar_id=} and with {expiration=} is in-place..."
    )
    request = service.events().watch(
        calendarId=calendar_id,
        maxResults=2500,
        orderBy="startTime",
        singleEvents=True,
        body=dict(
            kind="api#channel",
            type="web_hook",
            id=channel_id,
            address=web_hook_address,
            token=webhook_token,
            expiration=expiration,
        ),
    )
    response = request.execute()

    logger.debug(f"{response=}")

    resp_expiration_dt = datetime.fromtimestamp(int(response["expiration"]) // 1000)
    logger.info(
        f"Calendar events watch (id: {response['id']}) created! Expires: {resp_expiration_dt.strftime('%x %X')}"
    )

    return response
