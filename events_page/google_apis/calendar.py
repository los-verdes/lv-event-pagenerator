#!/usr/bin/env python
import base64
import re
import time
from datetime import datetime
from os.path import basename
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from dateutil.parser import parse
from googleapiclient.discovery import build
from logzero import setup_logger

from google_apis import load_credentials
from google_apis.drive import get_local_path_for_file

CALENDAR_RO_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


zoom_url_regexp = re.compile(r"https://[a-zA-Z0-9]+\.zoom.us\/.*")
game_regexp = re.compile(r"Austin FC (?P<vsat>vs|at) (?P<opponent>.*)")

today = datetime.today()

logger = setup_logger(name=__name__)


def build_service(credentials=None):
    if credentials is None:
        credentials = load_credentials()
    return build("calendar", "v3", credentials=credentials)


class Calendar(object):
    # Lazy caching by way of class attribute:
    events = None
    events_time_min = None
    events_time_max = None
    last_refresh = None

    def __init__(
        self, service, calendar_id, display_timezone, event_categories, mls_teams
    ) -> None:
        self._service = service
        self.calendar_id = calendar_id
        self.display_timezone = display_timezone
        self.event_categories = event_categories
        self.mls_teams = mls_teams
        self.cid = self.get_cid_from_id(self.calendar_id)
        self.categories_by_color_id = {}
        for name, event_category in event_categories.items():
            event_category["category_name"] = name
            color_id = event_category["gcal"]["color_id"]
            self.categories_by_color_id[color_id] = event_category
        logger.debug(f"{self.categories_by_color_id=}")

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
        return [e["category_name"] for e in self.events]

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
        self.last_refresh = datetime.now()

        mls_team_abbrs_by_name = {v["name"]: k for k, v in self.mls_teams.items()}
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
        for event in events:
            color_id = event.get("colorId", "0")
            # logger.debug(f"{color_id=} ({type(color_id)})")
            event["color_id"] = color_id
            event["css_classes"] = [
                f"category-{event['color_id']}",
                f"event-{event['id']}",
            ]
            if category := self.categories_by_color_id.get(event["color_id"]):
                # logger.debug(f"{event['color_id']=} => {category=}")
                event.update(category)

            for key in ["start", "end"]:
                event[key] = self.parse_event_timestamp(event, key)

            if event["start"] < today.replace(tzinfo=ZoneInfo(self.display_timezone)):
                event["in_past"] = True

            event["has_location"] = True
            if not event.get("location"):
                event["has_location"] = False

            event["has_description"] = False
            if event.get("description") is not None:
                event["has_description"] = True
                event["description_lines"] = event.get("description", "").split("\n")

            event["is_over_zoom"] = bool(
                zoom_url_regexp.match(event.get("location", ""))
            )

            if attachments := event.get("attachments"):
                for attachment in attachments:
                    if attachment["mimeType"].startswith("image/"):
                        # logger.debug(f"{attachment=}")
                        # TOOD: also ensure these files are downloaded at one point or another?
                        event["cover_image_filename"] = basename(
                            get_local_path_for_file(
                                attachment["fileId"], attachment["mimeType"]
                            )
                        )

            if summary_match := game_regexp.match(event["summary"]):
                groups = summary_match.groupdict()
                opp_abbr = mls_team_abbrs_by_name.get(groups["opponent"], "-")
                if groups["vsat"] == "vs":
                    event["match_slug"] = f"atxvs{opp_abbr}"
                else:
                    event["match_slug"] = f"{opp_abbr}vsatx"
            if event.get("category_name") is None:
                event["category_name"] = "misc"
        self.events = events
        return self.events

    def parse_event_timestamp(self, event, timestamp_key):
        parsed_dt = parse(
            event[timestamp_key].get("dateTime", event[timestamp_key].get("date"))
        )
        parsed_dt = parsed_dt.replace(tzinfo=ZoneInfo(self.display_timezone))
        return parsed_dt


def ensure_watch(
    service,
    calendar_id,
    channel_id,
    web_hook_address,
    webhook_token,
    expiration_in_days=None,
):
    current_seconds = time.time()
    added_seconds = expiration_in_days * 24 * 60 * 60
    expiration_seconds = current_seconds + added_seconds
    expiration = round(expiration_seconds * 1000)
    logger.debug(
        f"Ensure GCal events watch ({expiration=}) ({calendar_id=}) changes is in-place now..."
    )
    request = service.events().watch(
        calendarId=calendar_id,
        maxResults=2500,
        orderBy="startTime",
        singleEvents=True,
        # syncToken=,
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
    logger.debug(
        f"Watch (id: {response['id']}) created! Expires: {resp_expiration_dt.strftime('%x %X')}"
    )

    return response
