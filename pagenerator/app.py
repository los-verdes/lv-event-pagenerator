#!/usr/bin/env python
import calendar
import re
from datetime import datetime, timezone, timedelta
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

DEFAULT_CLUB_OPTA_ID = "15296"
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


# Add routes for serving up our static Ember frontend
# @app.route("/")
# def root():
#     return flask.send_from_directory("static", "index.html")


@app.route("/")
def home():
    calendar.setfirstweekday(calendar.SUNDAY)
    events = get_events(calendar_id=app.config["CALENDAR_ID"])
    the_date = datetime.today()
    calendar_dates = list(calendar.Calendar().itermonthdates(today.year, today.month))
    # events_dates = {e["start"] for e in events}
    events_by_date = defaultdict(list)
    events_by_month = defaultdict(list)
    for event in events:
        event_date = event["start"].date()
        # event_month = f"{event_date.month}-{event_date.year}"
        event_month = event["start"].strftime("%B %Y")
        events_by_date[event_date].append(event)
        events_by_month[event_month].append(event)
    calendar_date_events = []
    for calendar_date in calendar_dates:
        events_on_date = events_by_date[calendar_date]
        # breakpoint()
        active = calendar_date.month == the_date.month
        active &= calendar_date.year == the_date.year
        verde = len(events_on_date) > 0
        calendar_date_events.append(
            dict(
                datetime=calendar_date,
                num_events=len(events_on_date) if verde else "-",
                active=active,
                verde=verde,
                in_past=calendar_date < today.date(),
                events=events,
            )
        )
    team_schedule = grab_schedule(today.year)
    # breakpoint()
    #   {% for calendar_date_event in calendar_date_events if calendar_date_event.active %}
    #   {% for event in calendar_date_event.events %}
    return flask.render_template(
        "home.html",
        the_year=the_date.year,
        the_month=the_date.month,
        the_date=the_date,
        month_abbr=calendar.month_name[today.month],
        week_header=calendar.weekheader(3).split(),
        calendar_dates=list(
            calendar.Calendar().itermonthdates(today.year, today.month)
        ),
        calendar_date_events=calendar_date_events,
        events=events,
        events_by_month=events_by_month,
    )


EVENT_CSS_CLASSES = {
    "la murga": "lamurga-card",
    "lv all teams": "losverdes-card",
}


@app.route("/events")
def events():
    return flask.render_template(
        "events.html", events=get_events(calendar_id=app.config["CALENDAR_ID"])
    )


def grab_schedule(
    schedule_year,
    base_domain="sportapi.austinfc.com/api",
    club_opta_id=DEFAULT_CLUB_OPTA_ID,
):
    # if schedule_year is None:
    #     schedule_year = date.today().year
    matches = []
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
    logger.debug(f"{response=}")
    scheduled_matches = response.json()
    logger.debug(f"{scheduled_matches=}")
    # team_abbreviations = {}
    # for scheduled_match in scheduled_matches:
    #     scheduled_matches['away']['fullName']
    return {m["slug"]: m for m in scheduled_matches}
    return dict(
        matches={m["slug"]: m for m in scheduled_matches},
        # team_abbreviations=
    )


def get_events(calendar_id):
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

    if not events:
        return []

    zoom_url_regexp = re.compile(r"https://[a-zA-Z0-9]+\.zoom.us\/.*")
    game_regexp = re.compile(r"Austin FC (?P<vsat>vs|at) (?P<opponent>.*)")

    for event in events:
        for key in ["start", "end"]:
            event[key] = parse_event_timestamp(event, key)

        if event["start"] < today.replace(tzinfo=ZoneInfo("US/Central")):
            event["in_past"] = True

        event["has_location"] = True
        event["is_over_zoom"] = bool(zoom_url_regexp.match(event.get("location", "")))
        if not event.get("location"):
            event["has_location"] = False

        event["css_class"] = "event-card"
        for substr, css_class in EVENT_CSS_CLASSES.items():
            if substr in event["summary"].lower():
                event["css_class"] = css_class

        if summary_match := game_regexp.match(event["summary"]):
            groups = summary_match.groupdict()
            opp_abbr = TEAM_ABBREVIATIONS.get(groups['opponent'], '-')
            if groups["vsat"] == "vs":
                event[
                    "match_slug"
                ] = f"atxvs{opp_abbr}-{event['start'].strftime('%M-%D-%Y')}"
            else:
                event[
                    "match_slug"
                ] = f"{opp_abbr}vsatx-{event['start'].strftime('%M-%D-%Y')}"
    return events


def parse_event_timestamp(event, timestamp_key):
    parsed_dt = parse(
        event[timestamp_key].get("dateTime", event[timestamp_key].get("date"))
    )
    # parsed_dt.replace(tzinfo=timezone.utc)
    parsed_dt = parsed_dt.replace(tzinfo=ZoneInfo("US/Central"))
    # parsed_dt.astimezone(ZoneInfo('US/Central'))
    return parsed_dt


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
