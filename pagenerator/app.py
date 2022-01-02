#!/usr/bin/env python
import datetime
import os

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


@app.route("/events")
def events():
    global lv_events
    if lv_events is None:
        if app.config["USE_OAUTH_CREDS"]:
            credentials = load_local_creds()
        else:
            credentials, project = google.auth.default(GCLOUD_AUTH_SCOPES)
        lv_events = get_events(
            service=build("calendar", "v3", credentials=credentials),
            calendar_id=app.config["CALENDAR_ID"],
        )
    return flask.render_template("events.html", events=lv_events)


def get_events(service, calendar_id):
    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    logger.info("Getting the upcoming 10 events")
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=10,
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
        event["start"] = event["start"].get("dateTime", event["start"].get("date"))

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
