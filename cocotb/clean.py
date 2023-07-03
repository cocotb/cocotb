#!/usr/bin/env python

# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Clean cocotb build directories with CLI"""

import argparse
import os
import shutil
from pathlib import Path


def get_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "-r",
        "--recursive",
        default=False,
        help="recursive delete build folders",
        action="store_true",
    )
    parser.add_argument(
        "-d",
        "--dirname",
        default="sim_build",
        type=str,
        help="build folder name (default: %(default)s)",
    )

    return parser


def rm_build_folder(build_dir: Path):
    if os.path.isdir(build_dir):
        print("Removing:", build_dir)
        shutil.rmtree(build_dir, ignore_errors=True)


def main():
    parser = get_parser()
    args = parser.parse_args()

    dir = os.getcwd()
    rm_build_folder(os.path.join(dir, args.dirname))

    if args.recursive:
        dir = os.getcwd()
        for dir, _, _ in os.walk(dir):
            rm_build_folder(os.path.join(dir, args.dirname))


if __name__ == "__main__":
    main()
