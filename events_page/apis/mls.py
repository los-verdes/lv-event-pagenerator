#!/usr/bin/env python
from datetime import date

import requests
from logzero import logger

from apis import Singleton

DEFAULT_CLUB_OPTA_ID = "15296"


class TeamColors(metaclass=Singleton):
    _team_colors = {
        "atl": {"color": "#9d2235", "name": "Atlanta United"},
        "cin": {"color": "#003087", "name": "FC Cincinnati"},
        "clt": {"color": "#0085ca", "name": "Charlotte FC"},
        "col": {"color": "#8a2432", "name": "Colorado Rapids"},
        "dal": {"color": "#c6093b", "name": "FC Dallas"},
        "dc": {"color": "#212121", "name": "D.C. United"},
        "hou": {"color": "#101820", "name": "Houston Dynamo FC"},
        "la": {"color": "#004b87", "name": "LA Galaxy"},
        "lafc": {"color": "#212121", "name": "LAFC"},
        "mia": {"color": "#212322", "name": "Inter Miami CF"},
        "min": {"color": "#737b82", "name": "Minnesota United"},
        "mtl": {"color": "#212121", "name": "CF Montréal"},
        "nsh": {"color": "#201547", "name": "Nashville SC"},
        "orl": {"color": "#61259e", "name": "Orlando City"},
        "por": {"color": "#004812", "name": "Portland Timbers"},
        "rbny": {"color": "#ba0c2f", "name": "New York Red Bulls"},
        "rsl": {"color": "#001e61", "name": "Real Salt Lake"},
        "sea": {"color": "#64a608", "name": "Seattle Sounders FC"},
        "sj": {"color": "#0051ba", "name": "San Jose Earthquakes"},
        "skc": {"color": "#0c2340", "name": "Sporting Kansas City"},
        "van": {"color": "#002244", "name": "Vancouver Whitecaps FC"},
    }

    def team_abbrs_by_name(self):
        return {v["name"]: k for k, v in self._team_colors.items()}

    def to_dict(self):
        return {k: v["color"] for k, v in self._team_colors.items()}

    def get(self, key, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default

    def __getattr__(self, team_abbreviation):
        team_abbreviation = team_abbreviation.lower()
        return self._team_colors.get(team_abbreviation)


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
