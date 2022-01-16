#!/usr/bin/env python
import argparse
import logging

import logzero


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-q",
        "--quiet",
        help="modify output verbosity",
        action="store_true",
    )
    return parser


def parse_args(parser):
    args = parser.parse_args()

    if args.quiet:
        logzero.loglevel(logging.INFO)
    return args
