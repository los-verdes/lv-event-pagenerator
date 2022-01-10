#!/usr/bin/env python
import base64
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build
from dateutil.parser import parse

# from logzero import logger
from logzero import setup_logger


from google_utils import load_credentials
from google_utils.drive import get_local_path_for_file

CALENDAR_RO_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"

# Lazy caching by way of global var:
lv_events = None


zoom_url_regexp = re.compile(r"https://[a-zA-Z0-9]+\.zoom.us\/.*")
game_regexp = re.compile(r"Austin FC (?P<vsat>vs|at) (?P<opponent>.*)")

today = datetime.today()

logger = setup_logger(name=__name__)


def build_service(credentials=None):
    if credentials is None:
        credentials = load_credentials()
    return build("calendar", "v3", credentials=credentials)


def get_events(
    service,
    calendar_id,
    time_min,
    time_max,
    categories_by_color_id,
    mls_teams,
):
    global lv_events
    if lv_events is not None:
        return lv_events
    mls_team_abbrs_by_name = {v['name']: k for k, v in mls_teams.items()}
    logger.info(f"Getting the all events from {time_min} to {time_max}...")

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
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
        event["categories"] = []
        color_id = event.get("colorId", "default")
        # logger.debug(f"{color_id=} ({type(color_id)})")
        event["color_id"] = color_id
        event.update(categories_by_color_id[event["color_id"]])

        for key in ["start", "end"]:
            event[key] = parse_event_timestamp(event, key)

        if event["start"] < today.replace(tzinfo=ZoneInfo("US/Central")):
            event["in_past"] = True

        event["has_location"] = True
        if not event.get("location"):
            event["has_location"] = False

        event["has_description"] = False
        if event.get("description") is not None:
            event["has_description"] = True
            event["description_lines"] = event.get("description", "").split("\n")

        event["is_over_zoom"] = bool(zoom_url_regexp.match(event.get("location", "")))

        if attachments := event.get("attachments"):
            for attachment in attachments:
                if attachment["mimeType"].startswith("image/"):
                    # logger.debug(f"{attachment=}")
                    event["cover_image_filename"] = get_local_path_for_file(
                        attachment["fileId"], attachment["mimeType"]
                    )

        if summary_match := game_regexp.match(event["summary"]):
            groups = summary_match.groupdict()
            opp_abbr = mls_team_abbrs_by_name.get(groups["opponent"], "-")
            if groups["vsat"] == "vs":
                event["match_slug"] = f"atxvs{opp_abbr}"
            else:
                event["match_slug"] = f"{opp_abbr}vsatx"

    return events


def parse_event_timestamp(event, timestamp_key):
    parsed_dt = parse(
        event[timestamp_key].get("dateTime", event[timestamp_key].get("date"))
    )
    # parsed_dt.replace(tzinfo=timezone.utc)
    # TODO: set timezone via env var?
    parsed_dt = parsed_dt.replace(tzinfo=ZoneInfo("US/Central"))
    # parsed_dt.astimezone(ZoneInfo('US/Central'))
    return parsed_dt


def get_cid_from_id(calendar_id):
    calendar_id_bytes = calendar_id.encode("utf-8")
    cid_base64 = base64.b64encode(calendar_id_bytes)
    cid = cid_base64.decode().rstrip("=")
    return cid
