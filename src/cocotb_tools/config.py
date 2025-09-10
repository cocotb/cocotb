#!/usr/bin/env python
# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
Module for querying the cocotb configuration

This module provides information in module global variables and through a
``main()`` function that is used in the cocotb-config script.

Global variables:
    share_dir: str, path where the cocotb data is stored
    makefiles_dir: str, path where the cocotb makefiles are installed
    libs_dir: str, path where the cocotb interface libraries are located
"""

import argparse
import os
import sys
import textwrap
from pathlib import Path

import find_libpython

import cocotb_tools

base_tools_dir = Path(cocotb_tools.__file__).parent.resolve()
base_cocotb_dir = (base_tools_dir.parent / "cocotb").resolve()
if not (base_cocotb_dir.exists() and (base_cocotb_dir / "libs").exists()):
    import cocotb

    base_cocotb_dir = Path(cocotb.__file__).parent.resolve()

share_dir = base_cocotb_dir.joinpath("share")
libs_dir = base_cocotb_dir.joinpath("libs")
makefiles_dir = base_tools_dir.joinpath("makefiles")


def _get_version() -> str:
    import cocotb  # noqa: PLC0415

    return cocotb.__version__


def _help_vars_text() -> str:
    if "dev" in _get_version():
        doclink = "https://docs.cocotb.org/en/development/library_reference.html"
    else:
        doclink = f"https://docs.cocotb.org/en/v{_get_version()}/library_reference.html"

    # NOTE: make sure to keep "helpmsg" aligned with docs/source/library_reference.rst
    helpmsg = textwrap.dedent(
        """\
        The following variables are environment variables:

        cocotb
        ------
        COCOTB_TOPLEVEL           Instance in the hierarchy to use as the DUT
        COCOTB_RANDOM_SEED        Random seed, to recreate a previous test stimulus
        COCOTB_ANSI_OUTPUT        Force cocotb to print or not print in color
        COCOTB_REDUCED_LOG_FMT    Display log lines shorter
        COCOTB_ATTACH             Pause time value in seconds before the simulator start
        COCOTB_ENABLE_PROFILING   Performance analysis of the Python portion of cocotb
        COCOTB_LOG_LEVEL          Default logging level (default INFO)
        COCOTB_RESOLVE_X          How to resolve X, Z, U, W, - on integer conversion
        LIBPYTHON_LOC             Absolute path to libpython

        Regression Manager
        ------------------
        COCOTB_PDB_ON_EXCEPTION   Drop into the Python debugger (pdb) on exception
        COCOTB_TEST_MODULES       Module(s) to search for test functions (comma-separated)
        COCOTB_TESTCASE           Test function(s) to run (comma-separated list)
        COCOTB_RESULTS_FILE       File name for xUnit XML tests results
        COCOTB_USER_COVERAGE      Collect Python user coverage (HDL for some simulators)
        COVERAGE_RCFILE           Configuration for user code coverage

        GPI
        ---
        GPI_EXTRA                       Extra libraries to load at runtime (comma-separated)

        Scheduler
        ---------
        COCOTB_SCHEDULER_DEBUG         Enable additional output of coroutine scheduler
        COCOTB_TRUST_INERTIAL_WRITES   Trust inertial writes rather than mock them using scheduler

        For details, see {}"""
    ).format(doclink)
    return helpmsg


def lib_name(interface: str, simulator: str) -> str:
    """
    Return the name of interface library for given interface (VPI/VHPI/FLI) and simulator.
    """

    interface_name = interface.lower()
    supported_interfaces = ["vpi", "vhpi", "fli"]
    if interface_name not in supported_interfaces:
        raise ValueError(
            "Wrong interface used. Supported: " + ", ".join(supported_interfaces)
        )

    simulator_name = simulator.lower()
    supported_sims = [
        "icarus",
        "questa",
        "modelsim",
        "ius",
        "xcelium",
        "vcs",
        "ghdl",
        "riviera",
        "activehdl",
        "cvc",
        "nvc",
        "dsim",
    ]
    if simulator not in supported_sims:
        raise ValueError(
            "Wrong simulator name. Supported: " + ", ".join(supported_sims)
        )

    if simulator_name in ["questa", "cvc"]:
        library_name = "modelsim"
    elif simulator_name == "xcelium":
        library_name = "ius"
    elif simulator_name in ["riviera", "activehdl"]:
        library_name = "aldec"
    else:
        library_name = simulator_name

    if library_name == "icarus":
        lib_ext = ""
    elif os.name == "nt":
        lib_ext = ".dll"
    else:
        lib_ext = ".so"

    # check if compiled with msvc
    if (libs_dir / "cocotb.dll").is_file():
        lib_prefix = ""
    else:
        lib_prefix = "lib"

    return lib_prefix + "cocotb" + interface_name + "_" + library_name + lib_ext


def lib_name_path(interface: str, simulator: str) -> Path:
    """
    Return the absolute path of interface library for given interface (VPI/VHPI/FLI) and simulator
    """
    return libs_dir / lib_name(interface, simulator)


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--share",
        action="store_true",
        help="Print the path to cocotb's share directory",
    )
    group.add_argument(
        "--makefiles",
        action="store_true",
        help="Print the path to cocotb's makefile directory",
    )
    group.add_argument(
        "--python-bin",
        action="store_true",
        help="Print the path to the Python executable associated with the environment that cocotb is installed in.",
    )
    group.add_argument(
        "--help-vars",
        action="store_true",
        help="Print help about supported Makefile variables",
    )
    group.add_argument(
        "--libpython",
        action="store_true",
        help="Print the absolute path to the libpython associated with the current Python installation",
    )
    group.add_argument(
        "--lib-dir",
        action="store_true",
        help="Print the absolute path to the interface libraries location",
    )
    group.add_argument(
        "--lib-name",
        help="Print the name of interface library for given interface (VPI/VHPI/FLI) and simulator",
        nargs=2,
        metavar=("INTERFACE", "SIMULATOR"),
    )
    group.add_argument(
        "--lib-name-path",
        help="Print the absolute path of interface library for given interface (VPI/VHPI/FLI) and simulator",
        nargs=2,
        metavar=("INTERFACE", "SIMULATOR"),
    )
    group.add_argument(
        "--version",
        action="store_true",
        help="Print the version of cocotb",
    )

    return parser


def main() -> None:
    parser = _get_parser()
    args = parser.parse_args()

    if args.share:
        print(share_dir.as_posix())
    elif args.makefiles:
        print(makefiles_dir.as_posix())
    elif args.python_bin:
        print(Path(sys.executable).as_posix())
    elif args.help_vars:
        print(_help_vars_text())
    elif args.libpython:
        libpython_path = find_libpython.find_libpython()
        if libpython_path is None:
            sys.exit(1)
        print(Path(libpython_path).as_posix())
    elif args.lib_dir:
        print(libs_dir.as_posix())
    elif args.lib_name:
        print(lib_name(*args.lib_name))
    elif args.lib_name_path:
        print(lib_name_path(*args.lib_name_path).as_posix())
    elif args.version:
        print(_get_version())


if __name__ == "__main__":
    main()
