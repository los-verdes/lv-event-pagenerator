#!/usr/bin/env python

import os
from textwrap import dedent

from fastcore.basics import AttrDict
from fastcore.net import ExceptionsHTTP
from ghapi.all import GhApi
from logzero import logger
from tenacity import retry, stop_after_attempt, wait_fixed


def get_github_client(owner, repo, token):
    github_client = GhApi(
        owner=owner,
        repo=repo,
        token=token,
    )
    return github_client


def dispatch_build_workflow_run(
    github_client,
    workflow_filename: str,
    github_ref: str,
    site_hostname: str,
    cdn_zone_name: str,
) -> AttrDict:
    """Class-scoped fixture that dispatches the build workflow and returns the resulting workflow run."""
    # First get the full list of existing workflow runs (used subsequently to determine which workflow run is
    # dispatched as part of this 'build_suite_run').
    logger.debug(f"Grabbing extant workflow runs for {workflow_filename=}")
    try:
        list_runs_resp = github_client.actions.list_workflow_runs(
            workflow_id=workflow_filename
        )
        logger.debug(f"{list_runs_resp.total_count=}")
        extant_workflow_run_ids = [r.id for r in list_runs_resp.workflow_runs]
    except ExceptionsHTTP[404] as err:
        logger.error(
            f"HTTP404NotFoundError encountered ({err})! No workflow runs present?"
        )
        extant_workflow_run_ids = []

    dispatch_inputs = {
        "site_hostname": site_hostname,
        "cdn_zone_name": cdn_zone_name,
    }

    logger.debug(
        f"Dispatching {workflow_filename} with {github_ref=} and {dispatch_inputs=}"
    )

    github_client.actions.create_workflow_dispatch(
        workflow_id=workflow_filename,
        ref=github_ref,
        inputs=dispatch_inputs,
    )
    logger.info("Workflow dispatched")

    logger.debug("Grabbing updated workflow runs list post-dispatch...")
    workflow_run = poll_for_workflow_run(
        github_client, workflow_filename, extant_workflow_run_ids
    )

    # Once we've entered this post-yield portion of the method, all relevant build cases are complete and
    # we can start "teardown". I.e., ensuring the build workflow is completed one way or another here :)
    workflow_run = github_client.actions.get_workflow_run(workflow_run.id)
    return workflow_run


@retry(
    before=lambda r: logger.info(
        f"⌚️ Waiting until workflow run is discovered... Status check number: {r.attempt_number}"
    ),
    # Wait 15 seconds between polls, up to 60 times. I.e., 15 * 60 => 900s / 15m max polling time
    wait=wait_fixed(15),
    stop=stop_after_attempt(60),
)
def poll_for_workflow_run(
    github_client, workflow_filename: str, extant_workflow_run_ids: "list[str]"
) -> AttrDict:
    """Wait until dispatch workflow's run is discovered."""

    logger.debug(
        f"Grabbing workflow runs list, post dispatch, for {workflow_filename=}"
    )
    list_runs_resp = github_client.actions.list_workflow_runs(
        workflow_id=workflow_filename
    )
    logger.debug(f"{list_runs_resp.total_count=}")

    postdispatch_workflow_runs = {
        r.id: AttrDict(r) for r in list_runs_resp.workflow_runs
    }
    before_vs_after_diff = set(postdispatch_workflow_runs) - set(
        extant_workflow_run_ids
    )
    logger.debug(
        f"new workflow run IDs discovered since build run dispatched: {before_vs_after_diff=}"
    )

    assert len(before_vs_after_diff) > 0, "no build workflow run found after dispatch"
    assert (
        len(before_vs_after_diff) < 2
    ), "too many (>1) build workflow runs found after dispatch"

    github_workflow_run_id = before_vs_after_diff.pop()
    logger.debug(f"Found dispatched workflow with run ID: {github_workflow_run_id}")
    return postdispatch_workflow_runs[github_workflow_run_id]


@retry(
    before=lambda r: logger.info(
        f"🙏🏻 Waiting until workflow run reaches the desired status... Status check number: {r.attempt_number}"
    ),
    # Wait 15 seconds between polls, up to 60 times. I.e., 15 * 60 => 900s / 15m max polling time
    wait=wait_fixed(15),
    stop=stop_after_attempt(60),
)
def poll_for_workflow_run_status(
    github_client, workflow_run_id: str, desired_statuses: "list[str]"
) -> AttrDict:
    """Wait until build workflow run reaches the desired status(es)."""

    workflow_run = github_client.actions.get_workflow_run(workflow_run_id)
    logger.debug(f"{workflow_run.id=}: {workflow_run.status=} in {desired_statuses=}")
    logger.debug(f" => {workflow_run.status in desired_statuses=}")

    assert (
        workflow_run.status in desired_statuses
    ), f"{workflow_run.id=} has not yet reached {desired_statuses=}, current status: {workflow_run.status}"

    return AttrDict(workflow_run)


if __name__ == "__main__":
    import argparse
    import logging

    import logzero

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--quiet",
        help="modify output verbosity",
        action="store_true",
    )

    parser.add_argument(
        "--github_org",
        default="jeffwecan",
    )

    parser.add_argument(
        "--repo_name",
        default="lv-event-pagenerator",
    )

    parser.add_argument(
        "--github_ref",
        default="main",
    )

    parser.add_argument(
        "--workflow_filename",
        default="trigger_site_build.yml",
        help=dedent(
            """\
            Filename of the build workflow. E.g., 'some-workflow.yml'.
            Used as the `workflow_id` in related GitHub API calls.
            (As the filename is easier to divine than the numeric ID :)
            """
        ),
    )

    parser.add_argument(
        "-s",
        "--site-hostname",
        help="Fully-qualified domain name of the published site. Used in cache purging / priming methods.",
    )

    parser.add_argument(
        "-z",
        "--cdn-zone-name",
        help="Name of zone at CDN provider (Cloudflare only provider currently considered / supported).",
    )

    args = parser.parse_args()

    if args.quiet:
        logzero.loglevel(logging.INFO)

    github_client = get_github_client(
        owner=args.github_org,
        repo=args.repo_name,
        token=os.environ["GITHUB_PAT"],
    )

    workflow_run = dispatch_build_workflow_run(
        github_client=github_client,
        github_ref=args.github_ref,
        workflow_filename=args.workflow_filename,
        site_hostname=args.site_hostname,
        cdn_zone_name=args.cdn_zone_name,
    )
    logger.debug(f"result: {workflow_run=}")
