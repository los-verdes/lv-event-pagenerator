#!/usr/bin/env python
import re

import yaml
from logzero import logger
from google_utils import build_service, get_file_id
from urllib.parse import urlparse
from urllib.parse import parse_qs

GCLOUD_AUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive",
]

uri_regexp = re.compile(
    r"https://www.googleapis.com/drive/v3/files/(?P<file_id>[^?]+).*"
)


def process_drive_push_notification(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    print(f"{request.get_json()=}")
    print(f"{request.headers=}")
    push_notification = {
        h[0].lower().lstrip("x-goog-").replace("-", "_"): h[1]
        for h in request.headers
        if h[0].lower().startswith("x-goog")
    }
    print(f"{push_notification=}")
    print(f"{push_notification['resource_state']=}")
    print(f"{push_notification['resource_uri']=}")
    uri_matches = uri_regexp.match(push_notification["resource_uri"])
    print(f"{uri_matches=}")
    if not uri_matches:
        parsed_uri = urlparse(push_notification["resource_uri"])
        print(f"{parsed_uri=}")
        uri_params = parse_qs(parsed_uri.query)
        print(f"{uri_params=}")
        drive = build_service(
            service_name="drive",
            version="v3",
            scopes=GCLOUD_AUTH_SCOPES,
        )
        changes_page_token = uri_params["pageToken"][0]
        print(f"{changes_page_token=}")
        list_resp = drive.changes().list(pageToken=changes_page_token, pageSize=1).execute()
        print(f"{list_resp=}")
        breakpoint()
    #     return "uh oh"

    if uri_matches:
        print(f"{uri_matches.groupdict().get('file_id')=}")
        if file_id := uri_matches.groupdict().get("file_id"):
            drive = build_service(
                service_name="drive",
                version="v3",
                scopes=GCLOUD_AUTH_SCOPES,
            )
            file_resp = drive.files().get(fileId=file_id)
            logger.debug(f"{file_resp=}")
            print(f"{file_resp=}")
            # settings_fd = get_file_id(
            #     drive=drive,
            #     file_id=file_id,
            # )
            # settings_fd.seek(0)
            # settings = yaml.load(settings_fd, Loader=yaml.Loader)
            # print(f"{settings=}")

        # print(f"{json.dumps(request_json)}")
        # print("hi")
        return "Settings updates persisted! Diff is..."

    return "idk"


def local_invocation():
    example_headers = {
        "changes": [
            ("Host", "us-central1-losverdesatx-events.cloudfunctions.net"),
            (
                "User-Agent",
                "APIs-Google; (+https://developers.google.com/webmasters/APIs-Google.html)",
            ),
            ("Transfer-Encoding", "chunked"),
            ("Accept", "*/*"),
            ("Accept-Encoding", "gzip, deflate, br"),
            ("Forwarded", 'for="66.102.8.125";proto=https'),
            ("Function-Execution-Id", "jswhd7yg32y2"),
            ("Traceparent", "00-1cedd7863a4cf506da722549bfe8fefc-997f2f82cb2906a7-01"),
            ("X-Appengine-Country", "ZZ"),
            (
                "X-Appengine-Default-Version-Hostname",
                "bf93a26a9df85bba7p-tp.appspot.com",
            ),
            ("X-Appengine-Https", "on"),
            (
                "X-Appengine-Request-Log-Id",
                "61db45a800ff0e811fa32071110001737e6266393361323661396466383562626137702d7470000164366361323065613931643137613962336530306635333433336537336165353a3900010103",
            ),
            ("X-Appengine-Timeout-Ms", "599999"),
            ("X-Appengine-User-Ip", "66.102.8.125"),
            (
                "X-Cloud-Trace-Context",
                "1cedd7863a4cf506da722549bfe8fefc/11060611448645944999;o=1",
            ),
            ("X-Forwarded-For", "66.102.8.125"),
            ("X-Forwarded-Proto", "https"),
            ("X-Goog-Channel-Expiration", "Sun, 09 Jan 2022 21:27:33 GMT"),
            ("X-Goog-Channel-Id", "49e36c4f-db10-472d-bd4a-671ad8160b01"),
            ("X-Goog-Message-Number", "115256"),
            ("X-Goog-Resource-Id", "7aUp_6s8FLSeyTAud1QTxiHujBU"),
            ("X-Goog-Resource-State", "change"),
            (
                "X-Goog-Resource-Uri",
                "https://www.googleapis.com/drive/v3/changes?alt=json&includeCorpusRemovals=false&includeItemsFromAllDrives=false&includeRemoved=true&includeTeamDriveItems=false&pageSize=100&pageToken=791306&restrictToMyDrive=false&spaces=drive&supportsAllDrives=false&supportsTeamDrives=false&alt=json",
            ),
            ("Connection", "close"),
        ],
        "file": [
            ("Host", "us-central1-losverdesatx-events.cloudfunctions.net"),
            (
                "User-Agent",
                "APIs-Google; (+https://developers.google.com/webmasters/APIs-Google.html)",
            ),
            ("Transfer-Encoding", "chunked"),
            ("Accept", "*/*"),
            ("Accept-Encoding", "gzip, deflate, br"),
            ("Forwarded", 'for="74.125.215.95";proto=https'),
            ("Function-Execution-Id", "l4zb8mzzzjm6"),
            ("Traceparent", "00-5f11f0fb96c035aa65605fa0cee62d06-c9c01c36bcc7fe35-01"),
            ("X-Appengine-Country", "ZZ"),
            (
                "X-Appengine-Default-Version-Hostname",
                "bf93a26a9df85bba7p-tp.appspot.com",
            ),
            ("X-Appengine-Https", "on"),
            (
                "X-Appengine-Request-Log-Id",
                "61db243000ff07bbd8e64af2890001737e6266393361323661396466383562626137702d7470000164366361323065613931643137613962336530306635333433336537336165353a3900010101",
            ),
            ("X-Appengine-Timeout-Ms", "599999"),
            ("X-Appengine-User-Ip", "74.125.215.95"),
            (
                "X-Cloud-Trace-Context",
                "5f11f0fb96c035aa65605fa0cee62d06/14537650618572996149;o=1",
            ),
            ("X-Forwarded-For", "74.125.215.95"),
            ("X-Forwarded-Proto", "https"),
            ("X-Goog-Channel-Expiration", "Sun, 09 Jan 2022 19:06:40 GMT"),
            ("X-Goog-Channel-Id", "20418ccc-596f-4763-b1eb-233dc70409ab"),
            ("X-Goog-Message-Number", "1"),
            ("X-Goog-Resource-Id", "6DstUkjlE0PK0ewGPgOeFnqa-Po"),
            ("X-Goog-Resource-State", "sync"),
            (
                "X-Goog-Resource-Uri",
                "https://www.googleapis.com/drive/v3/files/1jJjp94KgQ7NtI0ds5SzpNKG3s2Y96dO8?acknowledgeAbuse=false&alt=json&supportsAllDrives=false&supportsTeamDrives=false&alt=json",
            ),
            ("Connection", "close"),
        ],
    }

    class MockRequest:
        def __init__(self, json, headers):
            self.json = json
            self._headers = headers

        def get_json(self):
            return self.json

        @property
        def headers(self):
            return self._headers

    print(f"{process_drive_push_notification(MockRequest({}, example_headers['changes']))}")
    # print(f"{process_drive_push_notification(MockRequest({}, example_headers['file']))}")
    # channels = [
    #     # dict(id="43c93f06-43e6-49a6-b025-d2a7b361da15", resource_id="6DstUkjlE0PK0ewGPgOeFnqa-Po"),
    #     # dict(id="49e36c4f-db10-472d-bd4a-671ad8160b01", resource_id="7aUp_6s8FLSeyTAud1QTxiHujBU"),
    #     # dict(id="79488884-63f3-4a60-bae3-162894ab1005", resource_id="7aUp_6s8FLSeyTAud1QTxiHujBU"),
    #     # dict(id="ccac5a6d-aa33-4652-aeb5-3bd0044f9c0f", resource_id="7aUp_6s8FLSeyTAud1QTxiHujBU"),
    #     # dict(id="d4d1124d-3f5e-459f-be1f-14c07baf8464", resource_id="6DstUkjlE0PK0ewGPgOeFnqa-Po"),
    #     # dict(id="26863d48-e828-45d2-a50d-07079c65eb16", resource_id="6DstUkjlE0PK0ewGPgOeFnqa-Po"),
    #     dict(id="fb331dbc-a6b6-476e-a2fb-4715ca8e45c9", resource_id="6DstUkjlE0PK0ewGPgOeFnqa-Po"),
    #     dict(id="e10ac58d-2cbc-431e-ba84-e69acd14ad53", resource_id="6DstUkjlE0PK0ewGPgOeFnqa-Po"),
    # ]
    # drive = build_service(
    #     service_name="drive",
    #     version="v3",
    #     scopes=GCLOUD_AUTH_SCOPES,
    # )
    # for channel in channels:
    #     print(drive.channels().stop(body=dict(id=channel["id"], resourceId=channel["resource_id"])).execute())


if __name__ == "__main__":
    local_invocation()
    breakpoint()
