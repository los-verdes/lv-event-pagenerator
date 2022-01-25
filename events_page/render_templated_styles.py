#!/usr/bin/env python
import os

import flask
from logzero import logger

from apis import calendar as gcal
from apis.drive import (add_category_image_file_metadata, build_service,
                        download_category_images, download_event_images)
from apis.mls import TeamColors
from config import cfg

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

    category_styling_by_name = {}

    for event_category in event_categories.values():
        class_name = f"category-{event_category['gcal_color_name']}"
        logger.debug(f"{class_name=} {event_category.get('cover_image_filename')}")

        # category_settings = default_category_settings.copy()
        category_styling = event_category["styling"].copy()
        if "file_metadata" in event_category and "cover_image" in category_styling:
            category_styling['cover_image'] = f"url({app.config['FREEZER_BASE_URL']}/static/{category_styling['cover_image']})"
        category_styling_by_name[class_name] = category_styling

    for event in calendar.events:
        class_name = event.event_specific_css_class
        logger.debug(f"{class_name=} {event.get('cover_image_filename')}")
        category_styling = dict()
        if cover_image_filename := event.cover_image_filename:
            category_styling[
                "cover_image"
            ] = f"url({app.config['FREEZER_BASE_URL']}/static/{cover_image_filename})"
            category_styling_by_name[class_name] = category_styling

    with app.app_context():
        rendered_scss = flask.render_template(
            "_vars.scss.j2",
            category_name_filters=category_name_filters,
            category_styling_by_name=category_styling_by_name,
            team_colors=team_colors.to_dict(),
        )

    logger.debug(f"{rendered_scss=}")
    output_path = os.path.join(BASE_DIR, "static", "scss", "_vars.scss")
    logger.info(f"Writing out templated scss to: {output_path=}")
    with open(output_path, "w") as f:
        f.write(rendered_scss)


def download_all_remote_images(drive_service, calendar, event_categories):
    downloaded_images = dict()
    downloaded_images.update(download_event_images(drive_service, calendar.events))
    downloaded_images.update(download_category_images(drive_service, event_categories))
    logger.info(f"download_all_remote_images() => {downloaded_images=}")
    return downloaded_images


def render_templated_styles(app, gcal_service, drive_service):
    logger.info("Rendering templated styles...")
    event_categories = cfg.event_categories
    event_categories = add_category_image_file_metadata(
        drive_service=drive_service, event_categories=event_categories
    )
    calendar = gcal.load_calendar(
        service=gcal_service,
        calendar_id=cfg.calendar_id,
    )
    download_all_remote_images(
        drive_service=drive_service,
        calendar=calendar,
        event_categories=event_categories,
    )
    render_scss_vars_template(
        app=app,
        calendar=calendar,
        event_categories=event_categories,
        team_colors=TeamColors(),
    )


if __name__ == "__main__":
    import cli
    from app import create_app

    cfg.load()
    args = cli.parse_args(cli.build_parser())

    render_templated_styles(
        app=create_app(),
        gcal_service=gcal.build_service(),
        drive_service=build_service(),
    )
