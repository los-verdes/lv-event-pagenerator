#!/usr/bin/env python
import base64
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from dateutil.parser import parse
from logzero import logger

from google_utils import build_service
from google_utils.drive import get_attachment

CALENDAR_RO_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"

COLOR_ID_CATEGORIES = {
    "0": {
        "categories": ["misc"],
        "cover_color": "#000000",
        "gcal_background": "#039be5",
        "gcal_name": None,
    },
    "1": {
        "categories": ["los-verdes"],
        "cover_color": "#000000",
        "gcal_background": "#a4bdfc",
        "gcal_name": "lavender",
    },
    "2": {
        "categories": ["la-murga"],
        "cover_color": "#000000",
        "gcal_background": "#7ae7bf",
        "gcal_name": "sage",
    },
    "3": {
        "categories": ["home-games"],
        "cover_color": "#000000",
        "gcal_background": "#dbadff",
        "gcal_name": "grape",
    },
    "4": {
        "categories": ["away-games"],
        "cover_color": "#000000",
        "gcal_background": "#ff887c",
        "gcal_name": "flamingo",
    },
    "5": {"gcal_background": "#fbd75b", "gcal_foreground": "#1d1d1d"},
    "6": {"gcal_background": "#ffb878", "gcal_foreground": "#1d1d1d"},
    "7": {"gcal_background": "#46d6db", "gcal_foreground": "#1d1d1d"},
    "8": {"gcal_background": "#e1e1e1", "gcal_foreground": "#1d1d1d"},
    "9": {"gcal_background": "#5484ed", "gcal_foreground": "#1d1d1d"},
    "10": {"gcal_background": "#51b749", "gcal_foreground": "#1d1d1d"},
    "11": {"gcal_background": "#dc2127", "gcal_foreground": "#1d1d1d"},
}

EVENT_CATEGORIES = {
    "la murga": "la-murga",
    "lv all teams": "los-verdes",
}

TEAM_ABBREVIATIONS = {
    "Atlanta United": "atl",
    "Austin FC": "atx",
    "CF Montréal": "mtl",
    "Charlotte FC": "clt",
    "Colorado Rapids": "col",
    "D.C. United": "dc",
    "FC Cincinnati": "cin",
    "FC Dallas": "dal",
    "Houston Dynamo FC": "hou",
    "Inter Miami CF": "mia",
    "LA Galaxy": "la",
    "Los Angeles Football Club": "lafc",
    "LAFC": "lafc",
    "Minnesota United": "min",
    "Nashville SC": "nsh",
    "New York Red Bulls": "rbny",
    "Orlando City": "orl",
    "Portland Timbers": "por",
    "Real Salt Lake": "rsl",
    "San Jose Earthquakes": "sj",
    "Seattle Sounders FC": "sea",
    "Sporting Kansas City": "skc",
    "Vancouver Whitecaps FC": "van",
}
# Lazy caching by way of global var:
lv_events = None


today = datetime.today()


def parse_event_timestamp(event, timestamp_key):
    parsed_dt = parse(
        event[timestamp_key].get("dateTime", event[timestamp_key].get("date"))
    )
    # parsed_dt.replace(tzinfo=timezone.utc)
    parsed_dt = parsed_dt.replace(tzinfo=ZoneInfo("US/Central"))
    # parsed_dt.astimezone(ZoneInfo('US/Central'))
    return parsed_dt


def get_calender_cid(calendar_id):
    calendar_id_bytes = calendar_id.encode("utf-8")
    cid_base64 = base64.b64encode(calendar_id_bytes)
    cid = cid_base64.decode().rstrip("=")
    return cid


def get_events(calendar_id, team_schedule, time_min, time_max):
    global lv_events
    if lv_events is not None:
        return lv_events

    logger.info("Getting the all events from {{ time_min }} to {{ time_max }}...")

    service = build_service(
        service_name="calendar",
        version="v3",
        scopes=[CALENDAR_RO_SCOPE],
    )
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
    # colors_result = service.colors().get().execute()
    # logger.debug(f"{colors_result=}")

    if not events:
        return []

    zoom_url_regexp = re.compile(r"https://[a-zA-Z0-9]+\.zoom.us\/.*")
    game_regexp = re.compile(r"Austin FC (?P<vsat>vs|at) (?P<opponent>.*)")

    for event in events:
        event["color_id"] = event.get("colorId", "0")
        event.update(COLOR_ID_CATEGORIES[event["color_id"]])
        # logger.debug(f'{event["color_id"]=} ({type(event["color_id"])}) {event.get("colorId", "0")=}')
        # event["categories"] = ["misc"]
        # event["css_classes"] = ["event-card"]

        for key in ["start", "end"]:
            event[key] = parse_event_timestamp(event, key)

        if event["start"] < today.replace(tzinfo=ZoneInfo("US/Central")):
            event["in_past"] = True

        event["has_location"] = True
        event["is_over_zoom"] = bool(zoom_url_regexp.match(event.get("location", "")))
        if not event.get("location"):
            event["has_location"] = False

        event["has_description"] = False
        if event.get("description") is not None:
            event["has_description"] = True
            event["description_lines"] = event.get("description", "").split("\n")

        # for substr, category in EVENT_CATEGORIES.items():
        #     if substr in event["summary"].lower():
        #         css_class = f"{category}-card"
        #         event["css_classes"].append(css_class)
        #         event["categories"] = [category]
        if attachments := event.get("attachments"):
            for attachment in attachments:
                if attachment["mimeType"].startswith("image/"):
                    logger.debug(f"{attachment=}")
                    event["cover_image_filename"] = attachment["title"]
                    fh = get_attachment(attachment)
                    if fh is not None:
                        event[
                            "cover_image_base64"
                        ] = f"data:{attachment['mimeType']};base64,{base64.b64encode(fh).decode()}"
            logger.debug(f"{event['summary']}:\n{attachments=}")
        event["is_atxfc_match"] = False
        if summary_match := game_regexp.match(event["summary"]):
            groups = summary_match.groupdict()
            opp_abbr = TEAM_ABBREVIATIONS.get(groups["opponent"], "-")
            # match_date_str = event["start"].strftime("%m-%d-%Y")
            if groups["vsat"] == "vs":
                # event["match_slug"] = f"atxvs{opp_abbr}-{match_date_str}"
                event["match_slug"] = f"atxvs{opp_abbr}"
                # event["css_classes"].append("event-home-game-card")
                # event["categories"] = ["home-games"]
            else:
                # event["match_slug"] = f"{opp_abbr}vsatx-{match_date_str}"
                event["match_slug"] = f"{opp_abbr}vsatx"
                # event["css_classes"].append("event-away-game-card")
                # event["categories"] = ["away-games"]

            # event["css_classes"].append(
            #     f"event-{event['match_slug'].split('-', 1)[0]}-card"
            # )
            if scheduled_match := team_schedule.get(event["match_slug"]):
                event["is_atxfc_match"] = True
                event["match_details"] = scheduled_match

    return events
