#!/usr/bin/env python
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import flask
from dateutil.parser import parse
from flask_assets import Bundle, Environment
from logzero import logger, setup_logger
from webassets.filter import get_filter

from google_utils import calendar as gcal
from google_utils import drive, load_credentials

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
# TODO: set to some rando public calendar instead for the generic usecase?
DEFAULT_CALENDAR_ID = "information@losverdesatx.org"
DEFAULT_TIMEZONE = "US/Central"

setup_logger(name=__name__)

app = flask.Flask(__name__)
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

SERVICE_ACCOUNT_CREDENTIALS = load_credentials()


@app.template_filter()
def parse_tz_datetime(datetime_str):
    return parse(datetime_str).replace(tzinfo=ZoneInfo(app.config["display_timezone"]))


@app.template_filter()
def replace_tz(datetime):
    return datetime.replace(tzinfo=ZoneInfo(app.config["display_timezone"]))


@app.template_filter()
def hex2rgb(hex, alpha=None):
    """Convert a string to all caps."""
    h = hex.lstrip("#")
    try:
        rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # noqa
    except Exception as err:
        logger.exception(f"unable to convert {hex=} to rgb: {err}")
        return h
    if alpha is None:
        return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
    else:
        return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"


@app.route("/")
def events():
    source_calendar_id = app.config["source_calendar_id"]
    calendar_service = gcal.build_service(SERVICE_ACCOUNT_CREDENTIALS)
    calendar = gcal.Calendar(
        service=calendar_service,
        calendar_id=source_calendar_id,
        display_timezone=app.config["display_timezone"],
        event_categories=app.config["event_categories"],
        mls_teams=app.config["mls_teams"],
    )

    # TODO: Should actually probably pull events <=24 hours ago start time so we don't drop events right after they start....
    events_time_min = datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events_time_max = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
    calendar.load_events(
        time_min=events_time_min,
        time_max=events_time_max,
    )
    logger.debug(f"{calendar.events=}")
    render_styles(app.config, calendar.events)
    return flask.render_template(
        "events.html",
        calendar=calendar,
    )


def create_app():
    # TODO: do this default settings thing better?
    default_settings = dict(
        source_calendar_id=DEFAULT_CALENDAR_ID,
        display_timezone=os.getenv("EVENTS_PAGE_TIMEZONE", DEFAULT_TIMEZONE),
        event_categories=dict(),
        mls_teams=dict(),
        FREEZER_STATIC_IGNORE=["*.scss", ".webassets-cache/*", ".DS_Store"],
        FREEZER_RELATIVE_URLS=True,
        FREEZER_REMOVE_EXTRA_FILES=True,
    )
    app.config.update(default_settings)

    drive_service = drive.build_service(SERVICE_ACCOUNT_CREDENTIALS)
    settings = drive.load_settings(drive_service)

    # Ensure all our category and event-specifc cover images are downloaded
    drive.download_all_images(drive_service)
    settings["event_categories"] = drive.download_category_images(
        drive_service, settings["event_categories"]
    )
    app.config.update(settings)

    return app


def render_styles(settings, events=None):
    category_names = [
        n
        for n, c in settings["event_categories"].items()
        if c.get("always_shown_in_filters")
    ]
    event_category_background_images = {}
    event_category_background_colors = {}
    event_category_text_fg_colors = {}
    event_category_text_bg_colors = {}

    base_url = "static/"
    if freezer_base_url := settings.get('FREEZER_BASE_URL'):
        base_url = f"{freezer_base_url}/static/"

    for event_category in settings["event_categories"].values():
        class_name = f"category-{event_category['gcal']['color_id']}"

        if cover_image_filename := event_category.get("cover_image_filename"):
            # event_category_background_images[class_name] = f"{base_url}/{cover_image_filename}"
            event_category_background_images[class_name] = cover_image_filename
        if bg_color := event_category.get("bg_color"):
            event_category_background_colors[class_name] = bg_color
        if text_fg_color := event_category.get("text_fg_color"):
            event_category_text_fg_colors[class_name] = text_fg_color
        if text_bg_color := event_category.get("text_bg_color"):
            event_category_text_bg_colors[class_name] = text_bg_color

    if events is not None:
        for event in events:
            class_name = f"event-{event['id']}"
            logger.debug(f"{class_name=} {event.get('cover_image_filename')}")
            if cover_image_filename := event.get("cover_image_filename"):
                event_category_background_images[class_name] = cover_image_filename

    with app.app_context():
        rendered_scss = flask.render_template(
            "_vars.scss.j2",
            team_colors={k: v["color"] for k, v in settings["mls_teams"].items()},
            category_names=category_names,  # TODO: should be passed event_categories for other styling bits
            event_category_background_images=event_category_background_images,
            event_category_background_colors=event_category_background_colors,
            event_category_text_fg_colors=event_category_text_fg_colors,
            event_category_text_bg_colors=event_category_text_bg_colors,
        )
    logger.debug(f"{rendered_scss=}")
    with open(os.path.join(BASE_DIR, "static", "scss", "_vars.scss"), "w") as f:
        f.write(rendered_scss)


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
