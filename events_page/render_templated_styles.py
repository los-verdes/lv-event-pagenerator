#!/usr/bin/env python
import os

import flask
from logzero import logger

from config import cfg
from google_apis import calendar as gcal
from google_apis.drive import (DriveSettings, add_category_image_file_metadata,
                               build_service, download_all_images_in_folder,
                               download_category_images)

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


def get_always_shown_categories(event_categories):
    always_shown_categories = {
        n for n, c in event_categories.items() if c.get("always_shown_in_filters")
    }
    return always_shown_categories


def render_scss_vars_template(app, calendar, event_categories, team_colors):
    if not event_categories:
        logger.warning(
            "No event categories provided in settings. Styling may be somewhat jank as a result. T.T"
        )

    category_name_filters = set(calendar.current_event_category_names)
    category_name_filters |= set(get_always_shown_categories(event_categories))
    category_name_filters = list(category_name_filters)

    logger.info(f"render_scss_vars_template() => {category_name_filters=}")

    event_category_background_images = {}
    event_category_background_colors = {}
    event_category_text_fg_colors = {}
    event_category_text_bg_colors = {}

    for event_category in event_categories.values():
        class_name = f"category-{event_category['gcal_color']['id']}"

        if cover_image_filename := event_category.get("cover_image_filename"):
            event_category_background_images[class_name] = cover_image_filename
        if bg_color := event_category.get("bg_color"):
            event_category_background_colors[class_name] = bg_color
        if text_fg_color := event_category.get("text_fg_color"):
            event_category_text_fg_colors[class_name] = text_fg_color
        if text_bg_color := event_category.get("text_bg_color"):
            event_category_text_bg_colors[class_name] = text_bg_color

    for event in calendar.events:
        class_name = event.event_specific_css_class
        # logger.debug(f"{class_name=} {event.get('cover_image_filename')}")
        if cover_image_filename := event.cover_image_filename:
            event_category_background_images[class_name] = cover_image_filename

    with app.app_context():
        rendered_scss = flask.render_template(
            "_vars.scss.j2",
            category_name_filters=category_name_filters,
            event_category_background_images=event_category_background_images,
            event_category_background_colors=event_category_background_colors,
            event_category_text_fg_colors=event_category_text_fg_colors,
            event_category_text_bg_colors=event_category_text_bg_colors,
            team_colors=team_colors,
        )

    logger.debug(f"{rendered_scss=}")
    output_path = os.path.join(BASE_DIR, "static", "scss", "_vars.scss")
    logger.info(f"Writing out templated scss to: {output_path=}")
    with open(output_path, "w") as f:
        f.write(rendered_scss)


def get_team_colors(drive_service):
    if mls_team_colors := DriveSettings(drive_service).mls_teams:
        return {k: v["color"] for k, v in mls_team_colors.items()}
    return dict()


def download_all_remote_images(drive_service, event_categories):
    downloaded_images = download_all_images_in_folder(drive_service, cfg.folder_name)
    downloaded_images += download_category_images(drive_service, event_categories)
    return downloaded_images


def render_templated_styles(app, gcal_service, drive_service):
    logger.info("Rendering templated styles...")
    event_categories = DriveSettings(drive_service).event_categories
    event_categories = add_category_image_file_metadata(
        drive_service=drive_service, event_categories=event_categories
    )
    render_scss_vars_template(
        app=app,
        calendar=gcal.load_calendar(
            service=gcal_service,
            calendar_id=cfg.calendar_id,
        ),
        event_categories=event_categories,
        team_colors=get_team_colors(drive_service),
    )
    download_all_remote_images(drive_service, event_categories)


if __name__ == "__main__":
    import argparse
    import logging

    import logzero

    from app import create_app

    cfg.load()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--quiet",
        help="modify output verbosity",
        action="store_true",
    )
    args = parser.parse_args()

    if args.quiet:
        logzero.loglevel(logging.INFO)

    render_templated_styles(
        app=create_app(),
        gcal_service=gcal.build_service(),
        drive_service=build_service(),
    )
