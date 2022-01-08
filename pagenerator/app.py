#!/usr/bin/env python
import base64
import io
import os
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import flask
import google.auth
import requests
from dateutil.parser import parse
from flask_assets import Bundle, Environment
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from logzero import logger, setup_logger

DEFAULT_CLUB_OPTA_ID = "15296"

EVENT_CATEGORIES = {
    "la murga": "la-murga",
    "lv all teams": "los-verdes",
}

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

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
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

# Reference: https://stackoverflow.com/a/33486003
# app.jinja_env.filters["quote_plus"] = lambda u: quote_plus(u)

# So we can read calendar entries and such:
GCLOUD_AUTH_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

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
    now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events_time_min = now
    events_time_max = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
    events = get_events(
        calendar_id=app.config["CALENDAR_ID"],
        # team_schedule=team_schedule,
        team_schedule=dict(),
        time_min=events_time_min,
        time_max=events_time_max,
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
    calendar_cid = get_calender_cid(app.config["CALENDAR_ID"])
    return flask.render_template(
        "home.html",
        calendar_id=app.config["CALENDAR_ID"],
        cal_id_href=f"https://calendar.google.com/calendar/embed?src={quote_plus(app.config['CALENDAR_ID'])}",
        calendar_cid=calendar_cid,
        cal_cid_href=f"https://calendar.google.com/calendar/u/0?cid={ calendar_cid }",
        events=events,
        default_categories=default_categories,
        additional_categories=list(event_categories - set(default_categories)),
        empty_categories=empty_categories,
        events_time_min=parse(events_time_min).replace(tzinfo=ZoneInfo("US/Central")),
        events_time_max=parse(events_time_max).replace(tzinfo=ZoneInfo("US/Central")),
    )


def get_calender_cid(calendar_id):
    calendar_id_bytes = calendar_id.encode("utf-8")
    cid_base64 = base64.b64encode(calendar_id_bytes)
    cid = cid_base64.decode().rstrip("=")
    return cid


def get_attachment(attachment):
    attachment_local_path = os.path.join(BASE_DIR, "static", attachment["title"])
    if os.path.exists(attachment_local_path):
        with open(attachment_local_path, "rb") as fh:
            return fh.read()

    if app.config["USE_OAUTH_CREDS"]:
        credentials = load_local_creds()
    else:
        credentials, project = google.auth.default(GCLOUD_AUTH_SCOPES)
    try:
        service = build("drive", "v3", credentials=credentials)

        request = service.files().get_media(fileId=attachment["fileId"])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))

        with open(attachment_local_path, "wb") as f:
            f.write(fh.getbuffer())
        return fh.getbuffer()
    except HttpError as error:
        # TODO(developer) - Handle errors from drive API.
        logger.exception(f"An error occurred: {error}")


def get_events(calendar_id, team_schedule, time_min, time_max):
    global lv_events
    if lv_events is not None:
        return lv_events
    if app.config["USE_OAUTH_CREDS"]:
        credentials = load_local_creds()
    else:
        credentials, project = google.auth.default(GCLOUD_AUTH_SCOPES)

    logger.info("Getting the all events from {{ time_min }} to {{ time_max }}...")

    service = build("calendar", "v3", credentials=credentials)
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
            match_date_str = event["start"].strftime("%m-%d-%Y")
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


colors_result = {
    "kind": "calendar#colors",
    "updated": "2012-02-14T00:00:00.000Z",
    "calendar": {
        "1": {"gcal_background": "#ac725e", "gcal_foreground": "#1d1d1d"},
        "2": {"gcal_background": "#d06b64", "gcal_foreground": "#1d1d1d"},
        "3": {"gcal_background": "#f83a22", "gcal_foreground": "#1d1d1d"},
        "4": {"gcal_background": "#fa573c", "gcal_foreground": "#1d1d1d"},
        "5": {"gcal_background": "#ff7537", "gcal_foreground": "#1d1d1d"},
        "6": {"gcal_background": "#ffad46", "gcal_foreground": "#1d1d1d"},
        "7": {"gcal_background": "#42d692", "gcal_foreground": "#1d1d1d"},
        "8": {"gcal_background": "#16a765", "gcal_foreground": "#1d1d1d"},
        "9": {"gcal_background": "#7bd148", "gcal_foreground": "#1d1d1d"},
        "10": {"gcal_background": "#b3dc6c", "gcal_foreground": "#1d1d1d"},
        "11": {"gcal_background": "#fbe983", "gcal_foreground": "#1d1d1d"},
        "12": {"gcal_background": "#fad165", "gcal_foreground": "#1d1d1d"},
        "13": {"gcal_background": "#92e1c0", "gcal_foreground": "#1d1d1d"},
        "14": {"gcal_background": "#9fe1e7", "gcal_foreground": "#1d1d1d"},
        "15": {"gcal_background": "#9fc6e7", "gcal_foreground": "#1d1d1d"},
        "16": {"gcal_background": "#4986e7", "gcal_foreground": "#1d1d1d"},
        "17": {"gcal_background": "#9a9cff", "gcal_foreground": "#1d1d1d"},
        "18": {"gcal_background": "#b99aff", "gcal_foreground": "#1d1d1d"},
        "19": {"gcal_background": "#c2c2c2", "gcal_foreground": "#1d1d1d"},
        "20": {"gcal_background": "#cabdbf", "gcal_foreground": "#1d1d1d"},
        "21": {"gcal_background": "#cca6ac", "gcal_foreground": "#1d1d1d"},
        "22": {"gcal_background": "#f691b2", "gcal_foreground": "#1d1d1d"},
        "23": {"gcal_background": "#cd74e6", "gcal_foreground": "#1d1d1d"},
        "24": {"gcal_background": "#a47ae2", "gcal_foreground": "#1d1d1d"},
    },
    "event": {
        "1": {"gcal_background": "#a4bdfc", "gcal_foreground": "#1d1d1d"},
        "2": {"gcal_background": "#7ae7bf", "gcal_foreground": "#1d1d1d"},
        "3": {"gcal_background": "#dbadff", "gcal_foreground": "#1d1d1d"},
        "4": {"gcal_background": "#ff887c", "gcal_foreground": "#1d1d1d"},
        "5": {"gcal_background": "#fbd75b", "gcal_foreground": "#1d1d1d"},
        "6": {"gcal_background": "#ffb878", "gcal_foreground": "#1d1d1d"},
        "7": {"gcal_background": "#46d6db", "gcal_foreground": "#1d1d1d"},
        "8": {"gcal_background": "#e1e1e1", "gcal_foreground": "#1d1d1d"},
        "9": {"gcal_background": "#5484ed", "gcal_foreground": "#1d1d1d"},
        "10": {"gcal_background": "#51b749", "gcal_foreground": "#1d1d1d"},
        "11": {"gcal_background": "#dc2127", "gcal_foreground": "#1d1d1d"},
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
