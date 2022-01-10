#!/usr/bin/env python
import os
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import flask
from dateutil.parser import parse
from flask_assets import Bundle, Environment
from logzero import setup_logger

from google_utils.calendar import get_calender_cid, get_events

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


def create_app():
    return app


if __name__ == "__main__":
    create_app()
    app.run(
        host="0.0.0.0",
        debug=True,
    )
