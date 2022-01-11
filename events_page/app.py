#!/usr/bin/env python
import itertools
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import flask
from dateutil.parser import parse
from flask_assets import Bundle, Environment
from logzero import logger, setup_logger
from google_utils import drive, load_credentials
from google_utils.calendar import Calendar, parsed_categories
from google_utils.calendar import build_service as build_calendar_service

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


@app.template_filter()
def hex2rgb(hex, alpha=None):
    """Convert a string to all caps."""
    h = hex.lstrip("#")
    try:
        rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    except:
        return h
    if alpha is None:
        return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
    else:
        return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"


@app.route("/")
def events():
    source_calendar_id = app.config["source_calendar_id"]
    image_files_by_id = app.config["IMAGE_FILES_BY_ID"]
    calendar_service = build_calendar_service(SERVICE_ACCOUNT_CREDENTIALS)
    calendar = Calendar(
        service=calendar_service,
        calendar_id=source_calendar_id,
        event_categories=app.config["event_categories"],
        mls_teams=app.config["mls_teams"],
    )
    now = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events_time_min = now
    events_time_max = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
    events = calendar.load_events(
        time_min=events_time_min,
        time_max=events_time_max,
    )

    return flask.render_template(
        "events.html",
        calendar=calendar,
        events=calendar.events,
        events_time_min=parse(events_time_min).replace(tzinfo=ZoneInfo("US/Central")),
        events_time_max=parse(events_time_max).replace(tzinfo=ZoneInfo("US/Central")),
        now=datetime.utcnow(),
    )


def create_app():
    # TODO: do this default settings thing better?
    default_settings = dict(
        source_calendar_id=DEFAULT_CALENDAR_ID,
        event_categories=dict(),
        mls_teams=dict(),
    )
    app.config.update(default_settings)

    drive_service = drive.build_service(SERVICE_ACCOUNT_CREDENTIALS)
    settings = drive.load_settings(drive_service)

    app.config.update(settings)
    image_files = drive.download_all_images(drive_service)
    app.config["IMAGE_FILES_BY_ID"] = {f["id"] for f in image_files}

    category_names = [
        n
        for n, c in settings["event_categories"].items()
        if c.get("always_shown_in_filters")
    ]
    with app.app_context():
        vars_scss = flask.render_template(
            "_vars.scss.j2",
            team_colors={k: v["color"] for k, v in settings["mls_teams"].items()},
            category_names=category_names,  # TODO: should be passed event_categories for other styling bits
            event_categories=parsed_categories(drive_service, settings["event_categories"]),
        )
    logger.debug(f"{vars_scss=}")
    with open(os.path.join(BASE_DIR, "static", "scss", "_vars.scss"), "w") as f:
        f.write(vars_scss)
    # with app.app_context():
    #     vars_scss = flask.render_template(
    #         "_vars.scss.j2",
    #         team_colors={k: v["color"] for k, v in settings["mls_teams"].items()},
    #     )
    #     logger.debug(f"{vars_scss=}")

    #     with open(os.path.join(BASE_DIR, "static", "scss", "_vars.scss"), "w") as f:
    #         f.write(vars_scss)
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
