# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import glob
import sys
from contextlib import suppress
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import nox

# Sessions run by default if nox is called without further arguments.
nox.options.sessions = ["dev_test"]

test_deps = ["pytest"]
coverage_deps = ["coverage", "pytest-cov"]
# gcovr 5.1 has an issue parsing some gcov files, so pin to 5.0. See
# https://github.com/gcovr/gcovr/issues/596
# When using gcovr 5.0, deprecated jinja2.Markup was removed in 3.1, so an
# Exception is raised during html report generation.
# See https://github.com/gcovr/gcovr/pull/576
# These issues are fixed on gcovr master branch, so next release should work.
coverage_report_deps = ["coverage", "jinja2<3.1", "gcovr==5.0"]

dev_deps = [
    "black",
    "isort",
    "mypy",
    "pre-commit",
    "nox",
    "flake8",
    "clang-format",
]

#
# Helpers for use within this file.
#


def simulator_support_matrix() -> List[Tuple[str, str, str]]:
    """
    Get a list of supported simulator/toplevel-language/GPI-interface tuples.
    """

    # Simulators with support for VHDL through VHPI, and Verilog through VPI.
    standard = [
        (sim, toplevel_lang, gpi_interface)
        for sim in ("activehdl", "rivierapro", "xcelium")
        for toplevel_lang in ("verilog", "vhdl")
        for gpi_interface in ("vpi", "vhpi")
        if (toplevel_lang, gpi_interface) in (("verilog", "vpi"), ("vhdl", "vhpi"))
    ]

    # Special-case simulators.
    special = [
        ("cvc", "verilog", "vpi"),
        ("ghdl", "vhdl", "vpi"),
        ("icarus", "verilog", "vpi"),
        ("questa", "verilog", "vpi"),
        ("questa", "vhdl", "fli"),
        ("questa", "vhdl", "vhpi"),
        ("verilator", "verilog", "vpi"),
        ("vcs", "verilog", "vpi"),
    ]

    return standard + special


def env_vars_for_test(
    sim: Optional[str], toplevel_lang: Optional[str], gpi_interface: Optional[str]
) -> Dict[str, str]:
    """Prepare the environment variables controlling the test run."""
    e = {}
    if sim is not None:
        e["SIM"] = sim
    if toplevel_lang is not None:
        e["TOPLEVEL_LANG"] = toplevel_lang
    assert not (toplevel_lang == "verilog" and gpi_interface != "vpi")
    if toplevel_lang == "vhdl" and gpi_interface is not None:
        e["VHDL_GPI_INTERFACE"] = gpi_interface

    return e


def stringify_dict(d: Dict[str, str]) -> str:
    return ", ".join(f"{k}={v}" for k, v in d.items())


def configure_env_for_dev_build(session: nox.session) -> None:
    """Set environment variables for a development build.

    - Enable coverage collection.
    - Build with more aggressive error checking.
    """
    session.env["CFLAGS"] = "-Werror -Wno-deprecated-declarations -g --coverage"
    session.env["COCOTB_LIBRARY_COVERAGE"] = "1"
    session.env["CXXFLAGS"] = "-Werror"
    session.env["LDFLAGS"] = "--coverage"


#
# Development pipeline
#
# - Use nox to build an sdist; no separate build step is required.
# - Run tests against the installed sdist.
# - Collect coverage.
#


@nox.session
def dev_build(session: nox.Session) -> None:
    session.warn("No building is necessary for development sessions.")


@nox.session
def dev_test(session: nox.Session) -> None:
    """Run all development tests as configured through environment variables."""

    dev_test_sim(session, sim=None, toplevel_lang=None, gpi_interface=None)
    dev_test_nosim(session)


@nox.session
@nox.parametrize("sim,toplevel_lang,gpi_interface", simulator_support_matrix())
def dev_test_sim(
    session: nox.Session,
    sim: Optional[str],
    toplevel_lang: Optional[str],
    gpi_interface: Optional[str],
) -> None:
    """Test a development version of cocotb against a simulator."""

    configure_env_for_dev_build(session)

    session.install(*test_deps, *coverage_deps)
    session.install("-e", ".")

    env = env_vars_for_test(sim, toplevel_lang, gpi_interface)
    config_str = stringify_dict(env)

    # Remove a potentially existing coverage file from a previous run for the
    # same test configuration.
    coverage_file = Path(f".coverage.test.sim-{sim}-{toplevel_lang}-{gpi_interface}")
    with suppress(FileNotFoundError):
        coverage_file.unlink()

    session.log(f"Running 'make test' against a simulator {config_str}")
    session.run("make", "clean", "test", external=True, env=env)

    session.log(f"Running simulator-specific tests against a simulator {config_str}")
    session.run(
        "pytest",
        "-v",
        "--cov=cocotb",
        "--cov-branch",
        # Don't display coverage report here
        "--cov-report=",
        "-k",
        "simulator_required",
    )
    Path(".coverage").rename(".coverage.pytest")

    session.log(f"All tests passed with configuration {config_str}!")

    # Combine coverage produced during the test runs, and place it in a file
    # with a name specific to this invocation of dev_test_sim().
    coverage_files = glob.glob("**/.coverage.cocotb", recursive=True)
    if not coverage_files:
        session.error(
            "No coverage files found. Something went wrong during the test execution."
        )
    coverage_files.append(".coverage.pytest")
    session.run("coverage", "combine", "--append", *coverage_files)
    Path(".coverage").rename(coverage_file)

    session.log(f"Stored Python coverage for this test run in {coverage_file}.")

    # Combine coverage from all nox sessions as last step after all sessions
    # have completed.
    session.notify("dev_coverage_combine")


@nox.session
def dev_test_nosim(session: nox.Session) -> None:
    """Run the simulator-agnostic tests against a cocotb development version."""

    configure_env_for_dev_build(session)

    session.install(*test_deps, *coverage_deps)
    session.install("-e", ".")

    # Remove a potentially existing coverage file from a previous run for the
    # same test configuration.
    coverage_file = Path(".coverage.test.pytest")
    with suppress(FileNotFoundError):
        coverage_file.unlink()

    # Run pytest with the default configuration in setup.cfg.
    session.log("Running simulator-agnostic tests with pytest")
    session.run(
        "pytest",
        "-v",
        "--cov=cocotb",
        "--cov-branch",
        # Don't display coverage report here
        "--cov-report=",
        "-k",
        "not simulator_required",
    )

    # Run pytest for files which can only be tested in the source tree, not in
    # the installed binary (otherwise we get an "import file mismatch" error
    # from pytest).
    session.log("Running simulator-agnostic tests in the source tree with pytest")
    pytest_sourcetree = [
        "cocotb/utils.py",
        "cocotb/binary.py",
        "cocotb/types/",
        "cocotb/_sim_versions.py",
    ]
    session.run(
        "pytest",
        "-v",
        "--doctest-modules",
        "--cov=cocotb",
        "--cov-branch",
        # Don't display coverage report here
        "--cov-report=",
        # Append to the .coverage file created in the previous pytest
        # invocation in this session.
        "--cov-append",
        "-k",
        "not simulator_required",
        *pytest_sourcetree,
    )

    session.log("All tests passed!")

    # Rename the .coverage file to make it unique for the
    Path(".coverage").rename(coverage_file)

    session.notify("dev_coverage_combine")


@nox.session
def dev_coverage_combine(session: nox.Session) -> None:
    """Combine coverage from previous dev_* runs into a .coverage file."""
    session.install(*coverage_report_deps)

    coverage_files = glob.glob("**/.coverage.test.*", recursive=True)
    session.run("coverage", "combine", *coverage_files)

    session.log("Wrote combined coverage database for all tests to '.coverage'.")

    session.notify("dev_coverage_report")


@nox.session
def dev_coverage_report(session: nox.Session) -> None:
    """Report coverage results."""
    session.install(*coverage_report_deps)

    session.log("Python coverage")
    session.run("coverage", "report")

    session.log("Library coverage")
    session.run("gcovr", "--print-summary", "--txt")


#
# Release pipeline.
#
# - Build wheels (release builds).
# - Install cocotb from wheel.
# - Run tests against cocotb installed from the wheel.
#
# The release pipeline does not collect coverage, and does not run doctests.
#

# Directory containing the distribution artifacts (sdist and bdist).
dist_dir = "dist"


@nox.session
def release_build(session: nox.Session) -> None:
    """Build a release (sdist and bdist)."""
    session.notify("release_build_bdist")
    session.notify("release_build_sdist")


@nox.session
def release_build_bdist(session: nox.Session) -> None:
    """Build a binary distribution (wheels) on the current operating system."""

    # Pin a version to ensure reproducible builds.
    session.install("cibuildwheel==2.5.0")

    # cibuildwheel only auto-detects the platform if it runs on a CI server.
    # Do the auto-detect manually to enable local runs.
    if sys.platform.startswith("linux"):
        platform = "linux"
    elif sys.platform == "darwin":
        platform = "macos"
    elif sys.platform == "win32":
        platform = "windows"
    else:
        session.error(f"Unknown platform: {sys.platform!r}")

    session.log("Building binary distribution (wheels)")
    session.run(
        "cibuildwheel",
        "--platform",
        platform,
        "--output-dir",
        dist_dir,
    )

    session.log(
        f"Binary distribution in release mode for {platform!r} built into {dist_dir!r}"
    )


@nox.session
def release_build_sdist(session: nox.Session) -> None:
    """Build the source distribution."""

    session.install("build")

    session.log("Building source distribution (sdist)")
    session.run("python", "-m", "build", "--sdist", "--outdir", dist_dir, ".")

    session.log(f"Source distribution in release mode built into {dist_dir!r}")


def release_install(session: nox.Session) -> None:
    """Helper: Install cocotb from wheels and also install test dependencies."""

    session.log(f"Installing cocotb from wheels in {dist_dir!r}")
    session.install(
        "--only-binary",
        "cocotb",
        "--no-index",
        "--find-links",
        dist_dir,
        "cocotb",
    )

    session.log("Running cocotb-config as basic installation smoke test")
    session.run("cocotb-config", "--version")

    session.log("Installing test dependencies")
    session.install(*test_deps)


@nox.session
@nox.parametrize("sim,toplevel_lang,gpi_interface", simulator_support_matrix())
def release_test_sim(
    session: nox.Session, sim: str, toplevel_lang: str, gpi_interface: str
) -> None:
    """Test a release version of cocotb against a simulator."""

    release_install(session)

    env = env_vars_for_test(sim, toplevel_lang, gpi_interface)
    config_str = stringify_dict(env)

    session.log(f"Running tests against a simulator: {config_str}")
    session.run("make", "clean", "test", external=True, env=env)

    session.log(f"Running simulator-specific tests against a simulator {config_str}")
    session.run(
        "pytest",
        "-v",
        "-k",
        "simulator_required",
    )

    session.log(f"All tests passed with configuration {config_str}!")


@nox.session
def release_test_nosim(session: nox.Session) -> None:
    """Run the simulator-agnostic tests against a cocotb release."""

    release_install(session)

    session.log("Running simulator-agnostic tests")
    session.run(
        "pytest",
        "-v",
        "-k",
        "not simulator_required",
    )

    session.log("All tests passed!")


@nox.session
def docs(session: nox.Session) -> None:
    """invoke sphinx-build to build the HTML docs"""
    session.install("-r", "documentation/requirements.txt")
    session.install("-e", ".")
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build", "./documentation/source", str(outdir), "--color", "-b", "html"
    )
    index = (outdir / "index.html").resolve().as_uri()
    session.log(f"Documentation is available at {index}")


@nox.session
def docs_linkcheck(session: nox.Session) -> None:
    """invoke sphinx-build to linkcheck the docs"""
    session.install("-r", "documentation/requirements.txt")
    session.install("-e", ".")
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build",
        "./documentation/source",
        str(outdir),
        "--color",
        "-b",
        "linkcheck",
    )


@nox.session
def docs_spelling(session: nox.Session) -> None:
    """invoke sphinx-build to spellcheck the docs"""
    session.install("-r", "documentation/requirements.txt")
    session.install("-e", ".")
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build",
        "./documentation/source",
        str(outdir),
        "--color",
        "-b",
        "spelling",
    )


@nox.session(reuse_venv=True)
def dev(session: nox.Session) -> None:
    """Build a development environment and optionally run a command given as extra args"""

    configure_env_for_dev_build(session)

    session.install(*test_deps)
    session.install(*dev_deps)
    session.install("-e", ".")
    if session.posargs:
        session.run(*session.posargs, external=True)
