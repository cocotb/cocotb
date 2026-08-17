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

from __future__ import annotations

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
        COCOTB_TOPLEVEL          Instance in the hierarchy to use as the DUT
        COCOTB_RANDOM_SEED       Random seed, to recreate a previous test stimulus
        COCOTB_ANSI_OUTPUT       Force cocotb to print or not print in color
        COCOTB_REDUCED_LOG_FMT   Display log lines shorter
        COCOTB_LOG_PREFIX        Set custom log prefix (f-string format)
        COCOTB_ATTACH            Pause time value in seconds before the simulator start
        COCOTB_ENABLE_PROFILING  Performance analysis of the Python portion of cocotb
        COCOTB_LOG_LEVEL         Default logging level (default INFO)
        COCOTB_RESOLVE_X         How to resolve X, Z, U, W, - on integer conversion

        Regression Manager
        ------------------
        COCOTB_PDB_ON_EXCEPTION  Drop into the Python debugger (pdb) on exception
        COCOTB_TEST_MODULES      Module(s) to search for test functions (comma-separated)
        COCOTB_TESTCASE          Test function(s) to run (Deprecated: Use COCOTB_TEST_FILTER)
        COCOTB_TEST_FILTER       Regex used to match test function names
        COCOTB_RESULTS_FILE      File name for xUnit XML tests results (default results.xml)
        COCOTB_USER_COVERAGE     Collect Python user coverage (HDL for some simulators)
        COVERAGE_RCFILE          Configuration for user code coverage
        COCOTB_REWRITE_ASSERTION_FILES
                                 Files to apply pytest assertion rewrites to (default *.py)
        COCOTB_MAX_FAILURES      Maximum number of test failures before aborting the regression
        COCOTB_LIST_TESTS        Prints all tests in the order they would be executed and exits
        COCOTB_RANDOM_TEST_ORDER Enables randomizing the order of tests within each stage

        Scheduler
        ---------
        COCOTB_SCHEDULER_DEBUG   Enable additional output of coroutine scheduler
        COCOTB_TRUST_INERTIAL_WRITES
                                 Trust inertial writes rather than mock them using scheduler

        GPI
        ---
        COCOTB_BOOTSTRAP  Ordered list of native libraries and entry points to load
        GPI_IMPL          Implementation libraries to load as part of GPI initialization
        GPI_LOG_LEVEL     Default logging level for "gpi" loggers (default INFO)
        GPI_DEBUG         Enable GPI debug features, including TRACE log output

        PYGPI
        -----
        PYGPI_USERS       List of Python callables to start test environment
        PYGPI_PYTHON_BIN  Python binary. Usually set automatically by test runner
        PYGPI_DEBUG       Enable PyGPI debug features, including TRACE log output

        For details, see {}"""
    ).format(doclink)
    return helpmsg


def bootstrap_entry(
    library: str | os.PathLike[str], entry_point: str | None = None
) -> str:
    """Format a library and optional entry point for ``COCOTB_BOOTSTRAP``."""
    library_str = Path(library).as_posix()
    for reserved in (",", os.pathsep):
        if reserved in library_str:
            raise ValueError(
                f"Library path {library_str!r} contains reserved character {reserved!r}"
            )

    if entry_point is None:
        return library_str
    if not entry_point or "," in entry_point or os.pathsep in entry_point:
        raise ValueError(f"Invalid bootstrap entry point {entry_point!r}")
    return f"{library_str},{entry_point}"


def _shared_library_path(name: str) -> Path:
    extension = ".dll" if os.name == "nt" else ".so"
    for prefix in ("", "lib"):
        library_path = libs_dir / f"{prefix}{name}{extension}"
        if library_path.is_file():
            return library_path
    raise FileNotFoundError(f"Shared library {name!r} not found")


def gpi_entry_point() -> str:
    """Return the libgpi entry for ``COCOTB_BOOTSTRAP``."""
    return bootstrap_entry(_shared_library_path("gpi"), "gpi_initialize")


def pygpi_entry_point() -> str:
    import cocotb.simulator  # noqa: PLC0415

    return bootstrap_entry(Path(cocotb.simulator.__file__).resolve(), "initialize")


def _gpi_impl_path(interface: str, simulator: str) -> Path:
    interface_name = interface.lower()
    supported_interfaces = ["vpi", "vhpi", "fli"]
    if interface_name not in supported_interfaces:
        raise ValueError(
            "Wrong interface used. Supported: " + ", ".join(supported_interfaces)
        )

    simulator_name = simulator.lower()
    supported_sims = [
        "icarus",
        "verilator",
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

    if os.name == "nt":
        lib_ext = ".dll"
    else:
        lib_ext = ".so"

    # check if compiled with msvc
    if (libs_dir / "gpi.dll").is_file():
        lib_prefix = ""
    else:
        lib_prefix = "lib"

    filename = f"{lib_prefix}cocotb{interface_name}_{library_name}{lib_ext}"
    return libs_dir / filename


def lib_entry(interface: str, simulator: str) -> str:
    """Return the bootstrap library and, when required, its entry function."""

    interface_name = interface.lower()
    simulator_name = simulator.lower()
    # Validate the interface and simulator names.
    _gpi_impl_path(interface_name, simulator_name)
    library = _shared_library_path("cocotb_bootstrap").as_posix()

    requires_entry_function = {
        ("vpi", "cvc"),
        ("vpi", "ius"),
        ("vpi", "xcelium"),
        ("vhpi", "activehdl"),
        ("vhpi", "riviera"),
    }

    if (interface_name, simulator_name) in requires_entry_function:
        return f"{library}:cocotb_bootstrap_entry"
    return library


def gpi_impl(simulator: str, *interfaces: str) -> str:
    """Return the comma-separated implementation entries for ``GPI_IMPL``."""
    if not interfaces:
        raise ValueError("At least one GPI interface is required")

    entries = []
    for interface in interfaces:
        interface_name = interface.lower()
        library = _gpi_impl_path(interface_name, simulator).as_posix()
        entries.append(f"{library}:cocotb{interface_name}_entry_point")
    return ",".join(entries)


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
        help="Print help about supported environment variables",
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
        "--lib-entry",
        help="Print the bootstrap library and, when required, its entry function for given interface (VPI/VHPI/FLI) and simulator",
        nargs=2,
        metavar=("INTERFACE", "SIMULATOR"),
    )
    group.add_argument(
        "--gpi-impl",
        help="Print the GPI_IMPL entries for the given simulator and interface(s) (VPI/VHPI/FLI)",
        nargs="+",
        metavar=("SIMULATOR", "INTERFACE"),
    )
    group.add_argument(
        "--gpi-entry-point",
        action="store_true",
        help="Print the libgpi entry point for use in COCOTB_BOOTSTRAP",
    )
    group.add_argument(
        "--pygpi-entry-point",
        action="store_true",
        help="Print the PyGPI entry point for use in COCOTB_BOOTSTRAP",
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
    elif args.lib_entry:
        print(lib_entry(*args.lib_entry))
    elif args.gpi_impl:
        simulator, *interfaces = args.gpi_impl
        if not interfaces:
            parser.error("--gpi-impl requires at least one interface")
        print(gpi_impl(simulator, *interfaces))
    elif args.gpi_entry_point:
        print(gpi_entry_point())
    elif args.pygpi_entry_point:
        print(pygpi_entry_point())
    elif args.version:
        print(_get_version())


if __name__ == "__main__":
    main()
