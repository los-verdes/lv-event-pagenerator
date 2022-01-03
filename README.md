# lv-event-pagenerator

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
