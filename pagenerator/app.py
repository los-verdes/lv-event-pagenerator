#!/usr/bin/env python
import calendar
import datetime
import os
from collections import defaultdict
from textwrap import dedent
from dateutil.parser import parse
import flask
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from logzero import logger, setup_logger

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


today = datetime.datetime.today()


@app.route("/")
def home():
    calendar.setfirstweekday(calendar.SUNDAY)
    events = get_events(calendar_id=app.config["CALENDAR_ID"])
    the_date = datetime.datetime.today()
    calendar_dates = list(calendar.Calendar().itermonthdates(today.year, today.month))
    # events_dates = {e["start"] for e in events}
    events_by_date = defaultdict(list)
    for event in events:
        events_by_date[event["start"].date()].append(event)
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
                num_events=len(events_on_date) if verde else '-',
                active=active,
                verde=verde,
                in_past=calendar_date < today.date(),
                events=events,
            )
        )

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
    )


@app.route("/events")
def events():
    return flask.render_template(
        "events.html", events=get_events(calendar_id=app.config["CALENDAR_ID"])
    )


def get_events(calendar_id):
    global lv_events
    if lv_events is not None:
        return lv_events
    if app.config["USE_OAUTH_CREDS"]:
        credentials = load_local_creds()
    else:
        credentials, project = google.auth.default(GCLOUD_AUTH_SCOPES)
    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    max_time = (
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).isoformat() + "Z"
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

    # Prints the start and name of the next 10 events
    for event in events:
        event["start"] = parse(event["start"].get("dateTime", event["start"].get("date")))
        event["end"] = parse(event["end"].get("dateTime", event["end"].get("date")))

    return events


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
