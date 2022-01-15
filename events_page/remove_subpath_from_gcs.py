#!/usr/bin/env python
from logzero import logger

from apis import storage

if __name__ == "__main__":
    import cli
    from config import cfg

    cfg.load()
    parser = cli.build_parser()
    args = cli.parse_args(parser)
    parser.add_argument(
        "-g",
        "--gcs-bucket-prefix",
        default=cfg.gcs_bucket_prefix,
        help="The GCS bucket prefix to publish the static site under.",
    )
    parser.add_argument(
        "-s",
        "--site-hostname",
        default=cfg.hostname,
        help="Fully-qualified domain name of the published site. Used in cache purging / priming methods.",
    )
    args = cli.parse_args(parser)

    storage.remove_subpath_from_gcs(
        client=storage.get_client(),
        bucket_id=args.site_hostname,
        prefix=args.gcs_bucket_prefix,
    )
    logger.info(
        f"Subpath deletion {args.gcs_bucket_prefix} for {args.site_hostname} completed! 🎉"
    )
