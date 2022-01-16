# lv-events-page

[![Deploy Infrastructure](https://github.com/jeffwecan/lv-event-pagenerator/actions/workflows/deploy_infrastrcture.yml/badge.svg)](https://github.com/jeffwecan/lv-event-pagenerator/actions/workflows/deploy_infrastrcture.yml)
[![Build and Publish Site](https://github.com/jeffwecan/lv-event-pagenerator/actions/workflows/build_and_publish_site.yml/badge.svg)](https://github.com/jeffwecan/lv-event-pagenerator/actions/workflows/build_and_publish_site.yml)

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

```hcl
# Suppose we needed this function scheduled daily or whatnot as well...
# > Notifications are not 100% reliable.
# > Expect a small percentage of messages to get dropped under normal working conditions.
# > Make sure to handle these missing messages gracefully, so that the application still
# > syncs even if no push messages are received.
# Reference: https://developers.google.com/calendar/api/guides/push#special-considerations
```

## Development

## Local Runs

Site builds expected to be performed within a GitHub Actions workflow for access to the requisite credentials, etc. To apply this repository's Terraform configuration or run a site build you'll first need:

- Access to the associated GCP project (for retriving settings and publishing content). This is done by inserting whatever username is associated with your [gcloud application-default credentials](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login) in the `gcp_project_editors` (or `gcp_project_owners`) lists defined in [losverdesatx-events.tfvars](losverdesatx-events.tfvars)
- Afterwards, be sure to set up `gcloud` and configure it for this project:

    ```shellsession
    $ gcloud auth application-default login
    $ gcloud config set project 'losverdesatx-events'
    Updated property [core/project].
    export EVENTS_PAGE_SA_EMAIL="$(terraform -chdir=terraform output -raw site_publisher_sa_email)"
    ./events_page/app.py
    ```

- [Optional] Install [just](https://github.com/casey/just)

### Applying Terraform

1. Export a couple of sensitive variables. Access to these secrets is not currently self-serve, so reach out to @jeffwecan to request values if needed (Actions workflow runs retrieve these credentials via repository secrets):

    ```shellsession
    export TF_VAR_cloudflare_api_token="..."
    export TF_VAR_site_publisher_gh_app_key="..."
    ```

2. Run your Terraform operation using just and the `run-tf` recipe. E.g.:

    ```shellsession
    $ just run-tf apply
    terraform -chdir="/Users/jeffwecan/workspace/lv-event-pagenerator/./terraform" apply -var-file=../losverdesatx-events.tfvars
    random_password.webhook_token: Refreshing state... [id=none]

    ###

    Do you want to perform these actions?
      Terraform will perform the actions described above.
      Only 'yes' will be accepted to approve.

      Enter a value: ...
    ```

### Viewing Site Locally

- To ensure consistency with automated runs, instruct the application to impersonate our GCP service account with the `EVENTS_PAGE_SA_EMAIL` env var:

    ```shellsession
    export EVENTS_PAGE_SA_EMAIL="$(terraform -chdir=terraform output -raw site_publisher_sa_email)"
    ```

- [Optional] If you want to use the local settings within [losverdesatx-events.tfvars](losverdesatx-events.tfvars), set the `EVENTS_PAGE_LOAD_LOCAL_TF_VARS` var as well:

    ```shellsession
    export EVENTS_PAGE_LOAD_LOCAL_TF_VARS="$PWD/losverdesatx-events.tfvars"
    ```

- Start up a local server with `just serve`. When making changes to event categories or cover images, you'll need to re-run this recipe to have those changes reflected. Otherwise, simply refreshing the page in a browser will pull in any HTML template changes, etc.:

    ```shellsession
    $ just serve
    just run-py './render_templated_styles.py'
    # export EVENTS_PAGE_SA_EMAIL="$(terraform -chdir=terraform output -raw site_publisher_sa_email)"
    cd "events_page" && ./render_templated_styles.py
    # ...
    * Serving Flask app 'app' (lazy loading)
    * Environment: production
      WARNING: This is a development server. Do not use it in a production deployment.
      Use a production WSGI server instead.
    * Debug mode: on
    * Running on all addresses.
      WARNING: This is a development server. Do not use it in a production deployment.
    * Running on http://192.168.86.31:5000/ (Press CTRL+C to quit)
    * Restarting with stat
    [D 220116 08:29:34 config:104] Config loaded from en...
    ```

## Deployment
