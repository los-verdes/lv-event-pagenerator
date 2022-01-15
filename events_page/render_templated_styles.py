#!/usr/bin/env python
import os

import flask
from logzero import logger

from apis import calendar as gcal
from apis.drive import (
    add_category_image_file_metadata,
    build_service,
    download_all_images_in_folder,
    download_category_images,
)
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
            team_colors=team_colors.to_dict(),
        )

    logger.debug(f"{rendered_scss=}")
    output_path = os.path.join(BASE_DIR, "static", "scss", "_vars.scss")
    logger.info(f"Writing out templated scss to: {output_path=}")
    with open(output_path, "w") as f:
        f.write(rendered_scss)


def download_all_remote_images(drive_service, event_categories):
    downloaded_images = download_all_images_in_folder(drive_service, cfg.folder_name)
    downloaded_images += download_category_images(drive_service, event_categories)
    downloaded_file_names = {f["name"]: f["mimeType"] for f in downloaded_images}
    logger.debug(f"download_all_remote_images() => {downloaded_file_names=}")
    return downloaded_images


def render_templated_styles(app, gcal_service, drive_service):
    logger.info("Rendering templated styles...")
    event_categories = cfg.event_categories
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
        team_colors=TeamColors(),
    )
    download_all_remote_images(drive_service, event_categories)


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
