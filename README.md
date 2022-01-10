# lv-events-page

## Deployment

### Pre-requisites

- GCP account / project?
- [`waypoint` CLI tool](https://www.waypointproject.io/downloads)

## Usage

1. Add an [embed block](https://support.squarespace.com/hc/en-us/articles/206543617-Embed-blocks) on the desired Squarespace page.
2. Set the block's code contents to:

    ```html
    <!-- This bit should be placed within an "embed" block over on ye 'ole Squarespace -->
    <div>
      <iframe id="lv-events-embed" width="100%" src="https://pagenerator-w7r57drkgq-uk.a.run.app/events" scrolling="no"></iframe>
    </div>
    ```

3. ???


```
/usr/local/Cellar/node/17.0.1/bin/sass style.scss | tee pagenerator/static/styles/style.css
```



I think the easiest arrangement is to use event "colors" for selecting the category and cover image for a given event. Going that route, there would basically be 11 potential color/category/image combos at our disposal:

| Color ID  | Color Name | Hex Code | LV Events Category | Cover Image                                   |
|-----------|------------|----------|--------------------|-----------------------------------------------|
| 1         | Lavender   | #7986cb  | los-verdes         | http://losverdesatx.org/images/some_image.png |
| 2         | Sage       | #33b679  | la-murga           | http://losverdesatx.org/images/some_image.png |
| 3         | Grape      | #8e24aa  | home-games         | http://losverdesatx.org/images/some_image.png |
| 4         | Flamingo   | #e67c73  | away-games         | http://losverdesatx.org/images/some_image.png |
| 5         | Banana     | #f6c026  | ???                | http://losverdesatx.org/images/some_image.png |
| 6         | Tangerine  | #f5511d  | ???                | http://losverdesatx.org/images/some_image.png |
| 7         | Peacock    | #039be5  | ???                | http://losverdesatx.org/images/some_image.png |
| 8         | Graphite   | #616161  | ???                | http://losverdesatx.org/images/some_image.png |
| 9         | Blueberry  | #3f51b5  | ???                | http://losverdesatx.org/images/some_image.png |
| 10        | Basil      | #0b8043  | ???                | http://losverdesatx.org/images/some_image.png |
| 11        | Tomato     | #d60000  | misc               | http://losverdesatx.org/images/some_image.png |

```shellsession
%▶ python -m pdb -c continue ./scripts/create_drive_watch.py -e 1
[D 220109 18:09:24 create_drive_watch:2] Using channel_id='lv-events-page-webhook'...
[D 220109 18:09:24 create_drive_watch:2] Ensure GDrive watch (expiration=1641859762404) for file_id=None is in-place now...
[D 220109 18:09:24 create_drive_watch:38] Ensure GDrive watch (expiration=1641859762404) (drive_id='1jJjp94KgQ7NtI0ds5SzpNKG3s2Y96dO8') changes is in-place now...
[D 220109 18:09:25 create_drive_watch:43] page_token_resp={'kind': 'drive#startPageToken', 'startPageToken': '2'}
[D 220109 18:09:25 create_drive_watch:62] response={'kind': 'api#channel', 'id': 'lv-events-page-webhook', 'resourceId': 'hWpl0OlfRWVAbo8DFtMBa_f0hUM', 'resourceUri': 'https://www.googleapis.com/drive/v3/changes?alt=json&includeCorpusRemovals=false&includeItemsFromAllDrives=false&includeRemoved=true&includeTeamDriveItems=false&pageSize=100&pageToken=2&restrictToMyDrive=false&spaces=drive&supportsAllDrives=false&supportsTeamDrives=false&alt=json', 'expiration': '1641776965000'}
[D 220109 18:09:25 create_drive_watch:65] Watch (id: lv-events-page-webhook) created! Expires: 01/09/22 19:09:25
[I 220109 18:09:25 create_drive_watch:2] Writing response data to: lv-events-page-webhook.json
--Return--
> /Users/jeffwecan/workspace/lv-event-pagenerator/scripts/create_drive_watch.py(2)<module>()->None
-> import json
```
