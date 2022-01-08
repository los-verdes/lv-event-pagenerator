#!/usr/bin/env python
import calendar
import itertools
import re
from datetime import datetime, timezone, timedelta, date
import os
from zoneinfo import ZoneInfo
from collections import defaultdict

import flask
import google.auth
from dateutil.parser import parse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from logzero import logger, setup_logger
import requests
from flask_assets import Environment, Bundle

DEFAULT_CLUB_OPTA_ID = "15296"

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
setup_logger(name=__name__)


app = flask.Flask(__name__)

assets = Environment(app)  # create an Environment instance
bundles = {  # define nested Bundle
    "style": Bundle(
        "scss/style.scss",
        filters="pyscss",
        output="style.css",
    )
}
assets.register(bundles)
app.config.update(
    DEPLOYMENT_ID=os.getenv("WAYPOINT_DEPLOYMENT_ID", "IDK"),
    CALENDAR_ID=os.getenv("CALENDAR_ID", "information@losverdesatx.org"),
    USE_OAUTH_CREDS=os.getenv("USE_OAUTH_CREDS", False),
)

# So we can read calendar entries and such:
GCLOUD_AUTH_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Lazy caching by way of global var:
lv_events = None


today = datetime.today()


@app.route("/")
def home():
    # team_schedule = grab_schedule(today.year)
    # css_bits = []
    # for slug, match in team_schedule.items():
    #     css_class = f"event-{slug.split('-', 1)[0]}-card"
    #     from textwrap import dedent
    #     rgb_home = tuple(int(match['home']['backgroundColor'].lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    #     css_bits.append(
    #         dedent(
    #             f"""\
    #             .{css_class}>.mdl-card__title {{
    #                 background-image: linear-gradient(125deg, {match['away']['backgroundColor']}, {match['home']['backgroundColor']});
    #             }}
    #             .{css_class} mark {{
    #                 padding: 2px;
    #                 color: white;
    #                 background-color: rgba({rgb_home[0]}, {rgb_home[1]}, {rgb_home[2]}, 0.75);
    #             }}

    #             """
    #         )
    #     )
    # with open("bits.css", "w") as bits:
    #     bits.write('\n'.join(css_bits))
    # breakpoint()
    # logger.debug(f"{list(team_schedule.keys())=}")
    events = get_events(
        calendar_id=app.config["CALENDAR_ID"],
        # team_schedule=team_schedule,
        team_schedule=dict(),
    )
    # categories = {c for c in itertools.chain.from_iterable(e['css_classes'] for e in events)}
    # categories = list(EVENT_CSS_CLASSES.keys()) + ["away games", "home games"]
    default_categories = [
        "los-verdes",
        "la-murga",
        "home-games",
        "away-games",
    ]
    event_categories = set()
    for event in events:
        event_categories |= set(event["categories"])
    all_categories = set(default_categories) | event_categories
    empty_categories = set(all_categories) - set(event_categories)
    return flask.render_template(
        "home.html",
        events=events,
        default_categories=default_categories,
        additional_categories=list(event_categories - set(default_categories)),
        empty_categories=empty_categories,
    )


def get_events(calendar_id, team_schedule):
    global lv_events
    if lv_events is not None:
        return lv_events
    if app.config["USE_OAUTH_CREDS"]:
        credentials = load_local_creds()
    else:
        credentials, project = google.auth.default(GCLOUD_AUTH_SCOPES)
    now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    max_time = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
    logger.info("Getting the upcoming 10 events")

    service = build("calendar", "v3", credentials=credentials)
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            timeMax=max_time,
            # maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])
    colors_result = service.colors().get().execute()
    logger.debug(f"{colors_result=}")

    if not events:
        return []

    zoom_url_regexp = re.compile(r"https://[a-zA-Z0-9]+\.zoom.us\/.*")
    game_regexp = re.compile(r"Austin FC (?P<vsat>vs|at) (?P<opponent>.*)")

    for event in events:
        event["categories"] = ["misc"]
        event["css_classes"] = ["event-card"]

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

        for substr, category in EVENT_CATEGORIES.items():
            if substr in event["summary"].lower():
                css_class = f"{category}-card"
                event["css_classes"].append(css_class)
                event["categories"] = [category]

        event["is_atxfc_match"] = False
        if summary_match := game_regexp.match(event["summary"]):
            groups = summary_match.groupdict()
            opp_abbr = TEAM_ABBREVIATIONS.get(groups["opponent"], "-")
            match_date_str = event["start"].strftime("%m-%d-%Y")
            if groups["vsat"] == "vs":
                event["match_slug"] = f"atxvs{opp_abbr}-{match_date_str}"
                event["css_classes"].append("event-home-game-card")
                event["categories"] = ["home-games"]
            else:
                event["match_slug"] = f"{opp_abbr}vsatx-{match_date_str}"
                event["css_classes"].append("event-away-game-card")
                event["categories"] = ["away-games"]

            event["css_classes"].append(
                f"event-{event['match_slug'].split('-', 1)[0]}-card"
            )
            if scheduled_match := team_schedule.get(event["match_slug"]):
                event["is_atxfc_match"] = True
                event["match_details"] = scheduled_match

    return events


colors_result = {
    "kind": "calendar#colors",
    "updated": "2012-02-14T00:00:00.000Z",
    "calendar": {
        "1": {"background": "#ac725e", "foreground": "#1d1d1d"},
        "2": {"background": "#d06b64", "foreground": "#1d1d1d"},
        "3": {"background": "#f83a22", "foreground": "#1d1d1d"},
        "4": {"background": "#fa573c", "foreground": "#1d1d1d"},
        "5": {"background": "#ff7537", "foreground": "#1d1d1d"},
        "6": {"background": "#ffad46", "foreground": "#1d1d1d"},
        "7": {"background": "#42d692", "foreground": "#1d1d1d"},
        "8": {"background": "#16a765", "foreground": "#1d1d1d"},
        "9": {"background": "#7bd148", "foreground": "#1d1d1d"},
        "10": {"background": "#b3dc6c", "foreground": "#1d1d1d"},
        "11": {"background": "#fbe983", "foreground": "#1d1d1d"},
        "12": {"background": "#fad165", "foreground": "#1d1d1d"},
        "13": {"background": "#92e1c0", "foreground": "#1d1d1d"},
        "14": {"background": "#9fe1e7", "foreground": "#1d1d1d"},
        "15": {"background": "#9fc6e7", "foreground": "#1d1d1d"},
        "16": {"background": "#4986e7", "foreground": "#1d1d1d"},
        "17": {"background": "#9a9cff", "foreground": "#1d1d1d"},
        "18": {"background": "#b99aff", "foreground": "#1d1d1d"},
        "19": {"background": "#c2c2c2", "foreground": "#1d1d1d"},
        "20": {"background": "#cabdbf", "foreground": "#1d1d1d"},
        "21": {"background": "#cca6ac", "foreground": "#1d1d1d"},
        "22": {"background": "#f691b2", "foreground": "#1d1d1d"},
        "23": {"background": "#cd74e6", "foreground": "#1d1d1d"},
        "24": {"background": "#a47ae2", "foreground": "#1d1d1d"},
    },
    "event": {
        "1": {"background": "#a4bdfc", "foreground": "#1d1d1d"},
        "2": {"background": "#7ae7bf", "foreground": "#1d1d1d"},
        "3": {"background": "#dbadff", "foreground": "#1d1d1d"},
        "4": {"background": "#ff887c", "foreground": "#1d1d1d"},
        "5": {"background": "#fbd75b", "foreground": "#1d1d1d"},
        "6": {"background": "#ffb878", "foreground": "#1d1d1d"},
        "7": {"background": "#46d6db", "foreground": "#1d1d1d"},
        "8": {"background": "#e1e1e1", "foreground": "#1d1d1d"},
        "9": {"background": "#5484ed", "foreground": "#1d1d1d"},
        "10": {"background": "#51b749", "foreground": "#1d1d1d"},
        "11": {"background": "#dc2127", "foreground": "#1d1d1d"},
    },
}
things = {
    "optaId": 2259030,
    "slug": "atxvscin-02-26-2022",
    "leagueMatchTitle": "",
    "home": {
        "optaId": 15296,
        "fullName": "Austin FC",
        "slug": "austin-fc",
        "shortName": "Austin",
        "abbreviation": "ATX",
        "backgroundColor": "#0BAC44",
        "logoBWSlug": "webcomp_9a2edba8-e187-4e39-a434-140896f1e9b5",
        "logoColorSlug": "webcomp_9fe50f89-c55f-47c7-b405-09d803fa5227",
        "logoColorUrl": "https://images.mlssoccer.com/image/upload/{formatInstructions}/v1614970762/assets/logos/15296-austin-logo_dcqfgn.png",
        "crestColorSlug": "webcomp_83f263dd-a78f-41ae-92ee-e48f68c9b575",
    },
    "away": {
        "optaId": 11504,
        "fullName": "FC Cincinnati",
        "slug": "fc-cincinnati",
        "shortName": "Cincinnati",
        "abbreviation": "CIN",
        "backgroundColor": "#003087",
        "logoBWSlug": "webcomp_093edcd5-74d9-4da2-93f8-d464f7169dd4",
        "logoColorSlug": "webcomp_553d2bce-a8cd-4cce-ada2-b6e07c74dc28",
        "logoColorUrl": "https://images.mlssoccer.com/image/upload/{formatInstructions}/v1620997960/assets/logos/CIN-Logo-480px.png",
        "crestColorSlug": "webcomp_41e2f018-d1fe-482e-bd36-9d2a02da24a0",
    },
    "venue": {
        "venueOptaId": "15488",
        "backgroundImageSlug": "",
        "name": "Q2 Stadium",
        "city": "Austin",
    },
    "season": {
        "slug": "us-major-league-soccer-season-2022-2023",
        "optaId": 2022,
        "competitionId": 98,
        "name": "Season 2022/2023",
    },
    "competition": {
        "optaId": 98,
        "name": "MLS Regular Season",
        "slug": "mls-regular-season",
        "shortName": "Regular Season",
        "matchType": "Regular",
        "logoLight": {"slug": ""},
        "logoDark": {"slug": ""},
        "blockHeaderName": "",
        "mgmId": "",
    },
    "broadcasters": [
        {
            "broadcasterTypeLabel": "Streaming",
            "broadcasterName": "MLS LIVE on ESPN+",
            "broadcasterStreamingURL": "https://plus.espn.com/soccer",
            "broadcasterType": "US Streaming",
        },
        {
            "broadcasterTypeLabel": "Streaming",
            "broadcasterName": "MLS LIVE on DAZN",
            "broadcasterStreamingURL": "https://www.dazn.com/en-CA/l/major-league-soccer/",
            "broadcasterType": "Canada Streaming",
        },
    ],
    "sponsorImage": {
        "assetUrl": "https://images.mlssoccer.com/image/upload/{formatInstructions}/v1623792033/assets/atx/Q2_IconOnly_wufazb.png"
    },
    "matchDate": "2022-02-26T23:00:00.0000000Z",
    "thirdPartyTickets": {
        "displayText": "Buy Tickets",
        "accessibleText": "Buy Tickets",
        "url": "https://seatgeek.com/fc-cincinnati-at-austin-fc-tickets/mls-mw/2022-02-26-5-pm/5582736?market=open&accountcredit=1&aid=15865&pid=austinfc&rid=211217&utm_medium=partnership&utm_source=austinfc_ticketing&utm_campaign=austinfc",
        "openInNewTab": True,
        "isVisible": False,
    },
    "promotionalSponsor": {
        "displayText": "Presented by Q2",
        "accessibleText": "Presented by Q2",
        "url": "q2.com/",
        "openInNewTab": True,
        "isVisible": False,
    },
    "tags": [],
    "homeClubBroadcasters": [],
    "awayClubBroadcasters": [],
    "clubBroadcasters": [],
    "isTimeTbd": False,
    "mgmId": "",
}


def parse_event_timestamp(event, timestamp_key):
    parsed_dt = parse(
        event[timestamp_key].get("dateTime", event[timestamp_key].get("date"))
    )
    # parsed_dt.replace(tzinfo=timezone.utc)
    parsed_dt = parsed_dt.replace(tzinfo=ZoneInfo("US/Central"))
    # parsed_dt.astimezone(ZoneInfo('US/Central'))
    return parsed_dt


def grab_schedule(
    schedule_year=None,
    base_domain="sportapi.austinfc.com/api",
    club_opta_id=DEFAULT_CLUB_OPTA_ID,
):
    if schedule_year is None:
        schedule_year = date.today().year
    request_url = f"https://{base_domain}/matches"
    logger.debug(
        f"Sending request to {request_url} ({schedule_year=}, {club_opta_id=})"
    )
    response = requests.get(
        url=request_url,
        params=dict(
            culture="en-us",
            dateFrom=f"{schedule_year - 1}-12-31",
            dateTo=f"{schedule_year}-12-31",
            clubOptaId=club_opta_id,
        ),
    )
    # logger.debug(f"{response=}")
    scheduled_matches = response.json()
    # logger.debug(f"{scheduled_matches=}")
    # team_abbreviations = {}
    # for scheduled_match in scheduled_matches:
    #     scheduled_matches['away']['fullName']
    return {m["slug"]: m for m in scheduled_matches}
    return dict(
        matches={m["slug"]: m for m in scheduled_matches},
        # team_abbreviations=
    )


def create_app():
    return app


def load_local_creds():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", GCLOUD_AUTH_SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", GCLOUD_AUTH_SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


if __name__ == "__main__":
    create_app()
    app.run(
        host="0.0.0.0",
        debug=True,
    )
