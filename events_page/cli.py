#!/usr/bin/env python
import argparse
import logging

import hcl
import logzero
from logzero import logger


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--quiet",
        help="modify output verbosity",
        action="store_true",
    )
    parser.add_argument(
        "-t",
        "--export-tfvars-to-defaults",
    )
    return parser


def parse_args(parser):
    args = parser.parse_args()

    if args.quiet:
        logzero.loglevel(logging.INFO)

    if tfvars_path := args.export_tfvars_to_defaults:
        from config import cfg
        with open(tfvars_path) as f:
            tfvars = hcl.load(f)
            if isinstance(tfvars, dict):
                cfg.defaults.update(tfvars)
            logger.info(f"Config after defaults loaded from {tfvars_path=}: {cfg.to_dict()=}")
            raise Exception(f"Unable to use {tfvars=} in Config defaults; not a map...")
    return args
