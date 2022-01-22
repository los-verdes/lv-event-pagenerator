#!/usr/bin/env python
from textwrap import dedent

from logzero import logger

from apis.github import (
    dispatch_build_workflow_run,
    get_github_client,
    SuperfluousDispatchException,
)
from apis.secrets import get_gh_app_key

if __name__ == "__main__":
    import cli
    from config import cfg

    cfg.load()
    parser = cli.build_parser()
    args = cli.parse_args(parser)

    parser.add_argument("--github_org", default=cfg.github_repo.split("/", 1)[0])

    parser.add_argument(
        "--repo_name",
        default=cfg.github_repo.split("/", 1)[1],
    )

    parser.add_argument(
        "--github_ref",
        default="main",
    )

    parser.add_argument(
        "--workflow_filename",
        default=cfg.build_workflow_filename,
        help=dedent(
            """\
            Filename of the build workflow. E.g., 'some-workflow.yml'.
            Used as the `workflow_id` in related GitHub API calls.
            (As the filename is easier to divine than the numeric ID :)
            """
        ),
    )
    args = cli.parse_args(parser)

    github_client = get_github_client(
        owner=args.github_org,
        repo=args.repo_name,
        app_id=int(cfg.githubapp_id),
        app_key=get_gh_app_key(),
        install_id=int(cfg.githubapp_install_id),
    )

    logger.info(
        f"Dispatching {args.workflow_filename} for {args.github_org}/{args.repo_name}..."
    )
    try:
        dispatched_workflow_run = dispatch_build_workflow_run(
            github_client=github_client,
            github_ref=args.github_ref,
            workflow_filename=args.workflow_filename,
        )
        logger.debug(f"result: {dispatched_workflow_run=}")
        logger.info(f"{dispatched_workflow_run.id=}: {dispatched_workflow_run.status=}")
    except SuperfluousDispatchException as err:
        logger.warning(f"SuperfluousDispatchException: {err=}")
