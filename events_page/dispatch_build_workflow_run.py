#!/usr/bin/env python
import os
from textwrap import dedent

from logzero import logger

from config import env
from github import dispatch_build_workflow_run, get_github_client

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
        default=env.github_repo.split("/", 1)[0]
    )

    parser.add_argument(
        "--repo_name",
        default=env.github_repo.split("/", 1)[0],
    )

    parser.add_argument(
        "--github_ref",
        default="main",
    )

    parser.add_argument(
        "--workflow_filename",
        default="build_and_publish_site.yml",
        help=dedent(
            """\
            Filename of the build workflow. E.g., 'some-workflow.yml'.
            Used as the `workflow_id` in related GitHub API calls.
            (As the filename is easier to divine than the numeric ID :)
            """
        ),
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
    )
    logger.debug(f"result: {workflow_run=}")
