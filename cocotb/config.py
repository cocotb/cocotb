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

import find_libpython

import cocotb

__all__ = ["share_dir", "makefiles_dir", "libs_dir"]


share_dir = os.path.join(os.path.dirname(cocotb.__file__), "share")
makefiles_dir = os.path.join(os.path.dirname(cocotb.__file__), "share", "makefiles")
libs_dir = os.path.join(os.path.dirname(cocotb.__file__), "libs")

# On Windows use mixed mode "c:/a/b/c" as this work in all cases
if os.name == "nt":
    libs_dir = libs_dir.replace("\\", "/")


def help_vars_text():
    if "dev" in cocotb.__version__:
        doclink = "https://docs.cocotb.org/en/latest/building.html"
    else:
        doclink = f"https://docs.cocotb.org/en/v{cocotb.__version__}/building.html"

    # NOTE: make sure to keep "helpmsg" aligned with documentation/source/building.rst
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
    COVERAGE                  Report Python coverage (also HDL for some simulators)

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

    # On Windows use mixed mode "c:/a/b/c" as this work in all cases
    if os.name == "nt":
        return library_name_path.replace("\\", "/")

    return library_name_path


def _findlibpython():
    libpython_path = find_libpython.find_libpython()
    if libpython_path is None:
        sys.exit(1)
    return libpython_path


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
    prefix_dir = os.path.dirname(os.path.dirname(cocotb.__file__))
    version = cocotb.__version__
    python_bin = sys.executable

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "--prefix",
        help="echo the package-prefix of cocotb",
        action=PrintAction,
        text=prefix_dir,
    )
    parser.add_argument(
        "--share",
        help="echo the package-share of cocotb",
        action=PrintAction,
        text=share_dir,
    )
    parser.add_argument(
        "--makefiles",
        help="echo the package-makefiles of cocotb",
        action=PrintAction,
        text=makefiles_dir,
    )
    parser.add_argument(
        "--python-bin",
        help="echo the path to the Python binary cocotb is installed for",
        action=PrintAction,
        text=python_bin,
    )
    parser.add_argument(
        "--help-vars",
        help="show help about supported variables",
        action=PrintAction,
        text=help_vars_text(),
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
        text=libs_dir,
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
        action=PrintAction,
        text=version,
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
