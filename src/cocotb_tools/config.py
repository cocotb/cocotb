#!/usr/bin/env python
###############################################################################
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

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
base_cocotb_dir = base_tools_dir.parent.joinpath("cocotb").resolve()
if not base_cocotb_dir.exists():
    import cocotb

    base_cocotb_dir = Path(cocotb.__file__).parent.resolve()

share_dir = base_cocotb_dir.joinpath("share")
libs_dir = base_cocotb_dir.joinpath("libs")
makefiles_dir = base_tools_dir.joinpath("makefiles")


def get_version() -> str:
    import cocotb

    return cocotb.__version__


def help_vars_text() -> str:
    if "dev" in get_version():
        doclink = "https://docs.cocotb.org/en/latest/building.html"
    else:
        doclink = f"https://docs.cocotb.org/en/v{get_version()}/building.html"

    # NOTE: make sure to keep "helpmsg" aligned with ../../docs/source/building.rst
    # Also keep it at 80 chars.
    helpmsg = textwrap.dedent(
        """\
    The following variables are environment variables:

    Cocotb
    ------
    TOPLEVEL                  Instance in the hierarchy to use as the DUT
    RANDOM_SEED               Random seed, to recreate a previous test stimulus
    COCOTB_ANSI_OUTPUT        Force cocotb to print or not print in color
    COCOTB_REDUCED_LOG_FMT    Display log lines shorter
    COCOTB_ATTACH             Pause time value in seconds before the simulator start
    COCOTB_ENABLE_PROFILING   Performance analysis of the Python portion of cocotb
    COCOTB_LOG_LEVEL          Default logging level (default INFO)
    COCOTB_RESOLVE_X          How to resolve X, Z, U, W on integer conversion
    MEMCHECK                  HTTP port to use for debugging Python memory usage
    LIBPYTHON_LOC             Absolute path to libpython

    Regression Manager
    ------------------
    COCOTB_PDB_ON_EXCEPTION   Drop into the Python debugger (pdb) on exception
    MODULE                    Modules to search for test functions (comma-separated)
    TESTCASE                  Test function(s) to run (comma-separated list)
    COCOTB_RESULTS_FILE       File name for xUnit XML tests results
    COVERAGE                  Collect Python user coverage (HDL for some simulators)
    COVERAGE_RCFILE           Configuration for user code coverage

    GPI
    ---
    GPI_EXTRA                 Extra libraries to load at runtime (comma-separated)

    Scheduler
    ---------
    COCOTB_SCHEDULER_DEBUG    Enable additional output of coroutine scheduler

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
    if os.path.isfile(os.path.join(libs_dir, "cocotb.dll")):
        lib_prefix = ""
    else:
        lib_prefix = "lib"

    return lib_prefix + "cocotb" + interface_name + "_" + library_name + lib_ext


def lib_name_path(interface, simulator):
    """
    Return the absolute path of interface library for given interface (VPI/VHPI/FLI) and simulator
    """
    library_name_path = os.path.join(libs_dir, lib_name(interface, simulator))

    return Path(library_name_path).as_posix()


def _findlibpython():
    libpython_path = find_libpython.find_libpython()
    if libpython_path is None:
        sys.exit(1)
    return Path(libpython_path).as_posix()


class PrintAction(argparse.Action):
    def __init__(self, option_strings, dest, text=None, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)
        self.text = text

    def __call__(self, parser, namespace, values, option_string=None):
        print(self.text)
        parser.exit()


class PrintFuncAction(argparse.Action):
    def __init__(self, option_strings, dest, function=None, **kwargs):
        super().__init__(option_strings, dest, **kwargs)
        self.function = function

    def __call__(self, parser, args, values, option_string=None):
        try:
            print(self.function(*values))
        except ValueError as e:
            parser.error(e)
        parser.exit()


def get_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--prefix",
        help="echo the package-prefix of cocotb",
        nargs=0,
        metavar=(),
        action=PrintFuncAction,
        function=lambda: base_cocotb_dir.parent.resolve().as_posix(),
    )
    parser.add_argument(
        "--share",
        help="echo the package-share of cocotb",
        action=PrintAction,
        text=share_dir.as_posix(),
    )
    parser.add_argument(
        "--makefiles",
        help="echo the package-makefiles of cocotb",
        action=PrintAction,
        text=makefiles_dir.as_posix(),
    )
    parser.add_argument(
        "--python-bin",
        help="echo the path to the Python binary cocotb is installed for",
        nargs=0,
        metavar=(),
        action=PrintFuncAction,
        function=lambda: Path(sys.executable).as_posix(),
    )
    parser.add_argument(
        "--help-vars",
        help="show help about supported variables",
        nargs=0,
        metavar=(),
        action=PrintFuncAction,
        function=help_vars_text,
    )
    parser.add_argument(
        "--libpython",
        help="Print the absolute path to the libpython associated with the current Python installation",
        nargs=0,
        metavar=(),
        action=PrintFuncAction,
        function=_findlibpython,
    )
    parser.add_argument(
        "--lib-dir",
        help="Print the absolute path to the interface libraries location",
        action=PrintAction,
        text=libs_dir.as_posix(),
    )
    parser.add_argument(
        "--lib-name",
        help="Print the name of interface library for given interface (VPI/VHPI/FLI) and simulator",
        nargs=2,
        metavar=("INTERFACE", "SIMULATOR"),
        action=PrintFuncAction,
        function=lib_name,
    )
    parser.add_argument(
        "--lib-name-path",
        help="Print the absolute path of interface library for given interface (VPI/VHPI/FLI) and simulator",
        nargs=2,
        metavar=("INTERFACE", "SIMULATOR"),
        action=PrintFuncAction,
        function=lib_name_path,
    )
    parser.add_argument(
        "-v",
        "--version",
        help="echo the version of cocotb",
        nargs=0,
        metavar=(),
        action=PrintFuncAction,
        function=get_version,
    )

    return parser


def main():
    parser = get_parser()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    parser.parse_args()


if __name__ == "__main__":
    main()
