#!/usr/bin/env python
from datetime import date

import requests
from logzero import logger

DEFAULT_CLUB_OPTA_ID = "15296"


def grab_schedule(
    schedule_year=None,
    base_domain="sportapi.austinfc.com/api",
    club_opta_id=DEFAULT_CLUB_OPTA_ID,
):
    if schedule_year is None:
        schedule_year = date.today().year
    request_url = f"https://{base_domain}/matches"
    logger.debug(
        f"Sending request to {request_url} ({schedule_year=}, {club_opta_id=})"
    )
    response = requests.get(
        url=request_url,
        params=dict(
            culture="en-us",
            dateFrom=f"{schedule_year - 1}-12-31",
            dateTo=f"{schedule_year}-12-31",
            clubOptaId=club_opta_id,
        ),
    )
    # logger.debug(f"{response=}")
    scheduled_matches = response.json()
    # logger.debug(f"{scheduled_matches=}")
    # team_abbreviations = {}
    # for scheduled_match in scheduled_matches:
    #     scheduled_matches['away']['fullName']
    return {m["slug"]: m for m in scheduled_matches}
    return dict(
        matches={m["slug"]: m for m in scheduled_matches},
        # team_abbreviations=
    )
