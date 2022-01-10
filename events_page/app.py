#!/usr/bin/env python
import itertools
import os
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import flask
from dateutil.parser import parse
from flask_assets import Bundle, Environment
from logzero import logger, setup_logger
from google_utils import calendar, drive, load_credentials

from webassets.filter import get_filter

# from flask_scss import Scss
# import sass

# from pydrive2.auth import GoogleAuth
setup_logger(name=__name__)

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
app = flask.Flask(__name__)
# Scss(app)

libsass = get_filter(
    "libsass",
    as_output=True,
    style="compressed",
)
assets = Environment(app)  # create an Environment instance
bundles = {  # define nested Bundle
    "style": Bundle(
        "scss/*.scss",
        filters=(libsass),
        output="style.css",
    )
}
assets.register(bundles)

# TODO: set to some rando public calendar instead for the generic usecase?
DEFAULT_CALENDAR_ID = "information@losverdesatx.org"

# Reference: https://stackoverflow.com/a/33486003
# app.jinja_env.filters["quote_plus"] = lambda u: quote_plus(u)

# So we can read calendar entries and such:
GCLOUD_AUTH_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

SERVICE_ACCOUNT_CREDENTIALS = load_credentials()


@app.route("/")
def events():
    now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events_time_min = now
    events_time_max = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
    source_calendar_id = app.config["source_calendar_id"]
    image_files_by_id = app.config["IMAGE_FILES_BY_ID"]
    calendar_service = calendar.build_service(SERVICE_ACCOUNT_CREDENTIALS)
    events = calendar.get_events(
        service=calendar_service,
        calendar_id=source_calendar_id,
        time_min=events_time_min,
        time_max=events_time_max,
        categories_by_color_id=app.config["categories_by_color_id"],
        mls_teams=app.config["mls_teams"],
    )
    # categories = {c for c in itertools.chain.from_iterable(e['css_classes'] for e in events)}
    # categories = list(EVENT_CSS_CLASSES.keys()) + ["away games", "home games"]
    logger.debug(f"{[c for c in app.config['categories_by_color_id'].values()]=}")
    default_categories = list(
        itertools.chain.from_iterable(
            [
                c["categories"]
                for c in app.config["categories_by_color_id"].values()
                if c.get("always_shown_in_filters")
            ]
        )
    )

    current_event_categories = set()
    for event in events:
        current_event_categories |= set(event["categories"])
    logger.debug(f"{current_event_categories=}")
    all_categories = set(default_categories) | current_event_categories
    empty_categories = set(all_categories) - set(current_event_categories)
    additional_categories = list(current_event_categories - set(default_categories))
    # logger.debug(f"")

    logger.debug(
        f"{default_categories=} {all_categories=} {empty_categories=} {additional_categories=}"
    )
    calendar_cid = calendar.get_cid_from_id(source_calendar_id)

    return flask.render_template(
        "events.html",
        calendar_id=source_calendar_id,
        cal_id_href=f"https://calendar.google.com/calendar/embed?src={quote_plus(app.config['source_calendar_id'])}",
        calendar_cid=calendar_cid,
        cal_cid_href=f"https://calendar.google.com/calendar/u/0?cid={ calendar_cid }",
        events=events,
        default_categories=list(default_categories),
        additional_categories=additional_categories,
        empty_categories=empty_categories,
        events_time_min=parse(events_time_min).replace(tzinfo=ZoneInfo("US/Central")),
        events_time_max=parse(events_time_max).replace(tzinfo=ZoneInfo("US/Central")),
        now=datetime.utcnow(),
    )


def create_app():
    # TODO: do this default settings thing better?
    default_settings = dict(
        source_calendar_id=DEFAULT_CALENDAR_ID,
        categories_by_color_id=dict(),
        mls_teams=dict(),
    )
    app.config.update(default_settings)

    drive_service = drive.build_service(SERVICE_ACCOUNT_CREDENTIALS)
    settings = drive.load_settings(drive_service)

    app.config.update(settings)
    image_files = drive.download_all_images(drive_service)
    app.config["IMAGE_FILES_BY_ID"] = {f["id"] for f in image_files}
    with app.app_context():
        vars_scss = flask.render_template(
            "_vars.scss.j2",
            team_colors={k: v["color"] for k, v in settings["mls_teams"].items()},
        )
        logger.debug(f"{vars_scss=}")

        with open(os.path.join(BASE_DIR, "static", "scss", "_vars.scss"), "w") as f:
            f.write(vars_scss)
    # logger.debug(f"{settings.keys()=}")
    # combined = {k: dict(color=v, name={v: k for k, v in settings['mls_team_abbreviations'].items()}.get(k)) for k, v in settings['mls_team_colors'].items()}
    # breakpoint()

    return app


if __name__ == "__main__":
    import logging

    for logger_name in ["google_utils.drive"]:
        logging.getLogger(logger_name).setLevel(logging.INFO)
    app = create_app()
    app.run(
        host="0.0.0.0",
        # debug=False,
        debug=True,
    )
