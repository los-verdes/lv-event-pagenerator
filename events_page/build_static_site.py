#!/usr/bin/env python
import logging
import os
import re

from googleapiclient.errors import HttpError
import logzero
from flask_frozen import Freezer
from logzero import logger

from app import create_app
from google_apis import build


def refresh_static_site():
    app = create_app()
    logger.debug(f"{app.config['FREEZER_BASE_URL']}")
    freeze_result = Freezer(app).freeze()
    logger.debug(f"{freeze_result=}")


if __name__ == "__main__":
    refresh_static_site()
    # purge_cache()
    # prime_cache()
