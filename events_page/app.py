#!/usr/bin/env python
from zoneinfo import ZoneInfo

import flask
from dateutil.parser import parse
from flask_assets import Bundle, Environment
from logzero import logger, setup_logger
from webassets.filter import get_filter

from config import cfg
from apis import calendar as gcal


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


@app.route("/")
def events():
    return flask.render_template(
        "index.html",
        calendar=gcal.load_calendar(
            service=gcal.build_service(),
            calendar_id=cfg.calendar_id,
        ),
    )


@app.template_filter()
def parse_tz_datetime(datetime_str):
    return parse(datetime_str).replace(tzinfo=ZoneInfo(app.config["display_timezone"]))


@app.template_filter()
def replace_tz(datetime_obj):
    return datetime_obj.replace(tzinfo=ZoneInfo(app.config["display_timezone"]))


@app.template_filter()
def hex2rgb(hex, alpha=None):
    """Convert a string to all caps."""
    if not hex.startswith("#"):
        return hex
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


def get_base_url():
    if prefix := cfg.gcs_bucket_prefix:
        return f"https://{cfg.hostname}/{prefix}"
    return f"https://{cfg.hostname}"


def create_app():
    cfg.load()

    # TODO: do this default settings thing better?
    default_app_config = dict(
        display_timezone=cfg.display_timezone,
        FREEZER_BASE_URL=get_base_url(),
        FREEZER_STATIC_IGNORE=["*.scss", ".webassets-cache/*", ".DS_Store"],
        FREEZER_RELATIVE_URLS=False,
        FREEZER_REMOVE_EXTRA_FILES=True,
    )
    logger.info(f"create_app() => {default_app_config=}")
    app.config.update(default_app_config)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        debug=True,
    )
