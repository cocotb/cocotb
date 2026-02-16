# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import glob
import os
import shutil
from contextlib import suppress
from pathlib import Path
from typing import cast

import nox

# Sessions run by default if nox is called without further arguments.
nox.options.sessions = ["dev_test"]

#
# Helpers for use within this file.
#


def simulator_support_matrix() -> list[tuple[str, str, str]]:
    """
    Get a list of supported simulator/toplevel-language/GPI-interface tuples.
    """

    # Simulators with support for VHDL through VHPI, and Verilog through VPI.
    standard = [
        (sim, toplevel_lang, gpi_interface)
        for sim in ("activehdl", "riviera", "xcelium", "vcs", "questa")
        for toplevel_lang, gpi_interface in (("verilog", "vpi"), ("vhdl", "vhpi"))
    ]

    # Special-case simulators.
    special = [
        ("cvc", "verilog", "vpi"),
        ("dsim", "verilog", "vpi"),
        ("ghdl", "vhdl", "vpi"),
        ("icarus", "verilog", "vpi"),
        ("nvc", "vhdl", "vhpi"),
        ("questa", "vhdl", "fli"),
        ("verilator", "verilog", "vpi"),
    ]

    return standard + special


def env_vars_for_test(
    sim: str, toplevel_lang: str, gpi_interface: str
) -> dict[str, str]:
    """Prepare the environment variables controlling the test run."""
    env = {
        "SIM": sim,
        "TOPLEVEL_LANG": toplevel_lang,
        "HDL_TOPLEVEL_LANG": toplevel_lang,
    }

    assert not (toplevel_lang == "verilog" and gpi_interface != "vpi")
    if toplevel_lang == "vhdl":
        env["VHDL_GPI_INTERFACE"] = gpi_interface

    # Do not fail on DeprecationWarning caused by virtualenv, which might come from
    # the site module.
    # Do not fail on DeprecationWarning caused by attrs dropping < 3.8 support
    # Do not fail on FutureWarning on Python < 3.9
    env["PYTHONWARNINGS"] = (
        "error,ignore::DeprecationWarning:site,"
        "ignore::DeprecationWarning:attr,"
        "ignore:Support for Python versions:FutureWarning:cocotb,"
    )
    # Test with debug enabled, but log level still set low. That way we can test the code
    # without slowing everything down by emitting roughly 1 million logs.
    env["COCOTB_SCHEDULER_DEBUG"] = "1"

    return env


def stringify_dict(d: dict[str, str]) -> str:
    return ", ".join(f"{k}={v}" for k, v in d.items())


#
# Development pipeline
#
# - Build cocotb with aggressive error checking and coverage flags.
# - Run doctests in the source tree with pytest.
# - Run simulator-agnostic tests with pytest.
# - Run simulator-specific tests and examples with pytest.
# - Run 'make test' to test Makefile-based tests.
# - Combine coverage from all test runs into a .coverage file.
# - Produce coverage reports from the combined .coverage file.
#


def configure_env_for_dev_test(session: nox.Session) -> None:
    """Set environment variables for a development test.

    - Enable coverage collection.
    """
    # Collect coverage of cocotb
    session.env["COCOTB_LIBRARY_COVERAGE"] = "1"


def build_cocotb_for_dev_test(session: nox.Session) -> None:
    """Build local cocotb for a development test.

    - Build with more aggressive error checking.
    """

    env = session.env.copy()
    flags = " ".join(
        [
            "-Werror",
            "-Wno-error=deprecated-declarations",
            "-Wsuggest-override",
            "-Og",
            "-g",
            "--coverage",
        ]
    )
    env["CFLAGS"] = flags
    env["CXXFLAGS"] = flags
    env["LDFLAGS"] = "--coverage"

    # Editable installs break C/C++ coverage collection; don't use them.
    # C/C++ coverage collection requires that the object files produced by the
    # compiler are not moved around, otherwise the gcno and gcda files produced
    # at compile and runtime, respectively, are located in the wrong
    # directories. Depending on the version of the Python install machinery
    # editable builds are done in a directory in /tmp, which is removed after
    # the build completes, taking all gcno files with them, as well as the path
    # to place the gcda files.
    session.install("-v", ".", env=env)


@nox.session
@nox.parametrize("sim,toplevel_lang,gpi_interface", simulator_support_matrix())
def dev_test(
    session: nox.Session,
    sim: str,
    toplevel_lang: str,
    gpi_interface: str,
) -> None:
    """Run all development tests and merge coverage."""
    session.install("--group", "dev_test")
    build_cocotb_for_dev_test(session)
    configure_env_for_dev_test(session)
    dev_test_nosim(session)
    dev_test_sim(session, sim, toplevel_lang, gpi_interface)
    dev_coverage_combine(session)


def dev_test_sim(
    session: nox.Session,
    sim: str,
    toplevel_lang: str,
    gpi_interface: str,
) -> None:
    """Test a development version of cocotb against a simulator."""

    env = env_vars_for_test(sim, toplevel_lang, gpi_interface)
    config_str = stringify_dict(env)

    # Remove a potentially existing coverage file from a previous run for the
    # same test configuration. Use a filename *not* starting with `.coverage.`,
    # as coverage.py assumes ownership over these files and deleted them at
    # will.
    coverage_file = Path(f".cov.test.sim-{sim}-{toplevel_lang}-{gpi_interface}")
    with suppress(FileNotFoundError):
        coverage_file.unlink()

    if "COCOTB_CI_SKIP_MAKE" not in os.environ:
        session.log(f"Running 'make test' against a simulator {config_str}")
        session.run("make", "-k", "test", external=True, env=env)

    # Run pytest for files which can only be tested in the source tree, not in
    # the installed binary (otherwise we get an "import file mismatch" error
    # from pytest).
    session.log("Running simulator-agnostic tests in the source tree with pytest")

    cocotb_pkg_dir = Path(
        cast(
            "str",
            session.run(
                "python",
                "-c",
                "import cocotb; print(cocotb.__file__)",
                env={"PYTHONWARNINGS": "ignore"},
                silent=True,
            ),
        ).strip()
    ).parent

    pytest_sourcetree = [
        str(cocotb_pkg_dir / "types"),
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
        *pytest_sourcetree,
    )

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
        env=env,
    )
    Path(".coverage").rename(".coverage.pytest")

    session.log(f"Running examples against a simulator {config_str}")
    pytest_example_tree = [
        "examples/adder",
        "examples/simple_dff",
        "examples/matrix_multiplier",
        "examples/mixed_language",
    ]
    session.run(
        "pytest",
        "-v",
        *pytest_example_tree,
        env=env,
    )

    # We need to run it separately to avoid loading pytest cocotb plugin for other tests
    session.log(f"Running tests for pytest plugin against a simulator {config_str}")
    session.run(
        "pytest",
        "-v",
        "tests/pytest_plugin",
        "--cocotb-simulator",
        sim,
        "--cocotb-gpi-interfaces",
        gpi_interface,
        "--cocotb-toplevel-lang",
        toplevel_lang,
        env=env,
    )

    session.log(f"All tests and examples passed with configuration {config_str}!")

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


def dev_test_nosim(session: nox.Session) -> None:
    """Run the simulator-agnostic tests against a cocotb development version."""

    # Remove a potentially existing coverage file from a previous run for the
    # same test configuration. Use a filename *not* starting with `.coverage.`,
    # as coverage.py assumes ownership over these files and deleted them at
    # will.
    coverage_file = Path(".cov.test.nosim")
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

    session.log("All tests passed!")

    # Rename the .coverage file to make it unique to the session.
    Path(".coverage").rename(coverage_file)

    session.log(f"Stored Python coverage for this test run in {coverage_file}.")


def dev_coverage_combine(session: nox.Session) -> None:
    """Combine coverage from previous dev_* runs into a .coverage file."""

    coverage_files = glob.glob("**/.cov.test.*", recursive=True)
    session.run("coverage", "combine", *coverage_files)
    assert Path(".coverage").is_file()

    session.log("Wrote combined coverage database for all tests to '.coverage'.")


@nox.session
def dev_coverage_report(session: nox.Session) -> None:
    """Report coverage results."""
    session.install("--group", "coverage_report")

    # combine coverage files from previous dev_test runs, if not already done
    if not Path(".coverage").is_file():
        dev_coverage_combine(session)

    # Produce Cobertura XML coverage reports.
    session.log("Producing Python and C/C++ coverage in Cobertura XML format")

    coverage_python_xml = Path(".python_coverage.xml")
    session.run("coverage", "xml", "-o", str(coverage_python_xml))
    assert coverage_python_xml.is_file()

    if session.posargs:
        gcov_executable_args = [
            "--gcov-executable",
            session.posargs[0],
        ]
    else:
        gcov_executable_args = []
    coverage_cpp_xml = Path(".cpp_coverage.xml")
    session.run(
        "gcovr",
        "--cobertura",
        "--output",
        str(coverage_cpp_xml),
        ".",
        *gcov_executable_args,
    )
    assert coverage_cpp_xml.is_file()

    session.log(
        f"Cobertura XML files written to {str(coverage_cpp_xml)!r} (C/C++) and {str(coverage_python_xml)!r} (Python)"
    )

    # Report human-readable coverage.
    session.log("Python coverage")
    session.run("coverage", "report")

    session.log("Library coverage")
    session.run(
        "gcovr",
        "--print-summary",
        "--txt",
        *gcov_executable_args,
    )


#
# Release pipeline.
#
# - Clean out the dist directory.
# - Build wheels (release builds).
# - Install cocotb from wheel.
# - Run tests against cocotb installed from the wheel.
#
# The release pipeline does not collect coverage, and does not run doctests.
#

# Directory containing the distribution artifacts (sdist and bdist).
dist_dir = "dist"


@nox.session
def release_clean(session: nox.Session) -> None:
    """Remove all build artifacts from the dist directory."""
    shutil.rmtree(dist_dir, ignore_errors=True)


@nox.session
def release_build_wheel(session: nox.Session) -> None:
    """Build a binary distribution (wheels) on the current operating system."""

    session.install("--group", "release_build_wheel")

    session.log("Building binary distributions (wheels)")
    session.run(
        "cibuildwheel",
        "--output-dir",
        dist_dir,
    )

    session.log(f"Binary distribution in release mode built into {dist_dir!r}")


@nox.session
def release_build_sdist(session: nox.Session) -> None:
    """Build the source distribution."""

    session.install("--group", "release_build_sdist")

    session.log("Building source distribution (sdist)")
    session.run("python", "-m", "build", "--sdist", "--outdir", dist_dir, ".")

    session.log(f"Source distribution in release mode built into {dist_dir!r}")


@nox.session
def release_test_sdist(session: nox.Session) -> None:
    """Build and install the sdist."""

    # Find the sdist to install.
    sdists = list(Path(dist_dir).glob("cocotb-*.tar.gz"))
    if not sdists:
        session.notify("release_build_sdist")
        sdists = list(Path(dist_dir).glob("cocotb-*.tar.gz"))
    if len(sdists) > 1:
        session.error(
            f"More than one potential sdist found in the {dist_dir!r} "
            f"directory. Run the 'release_clean' session first!"
        )
    sdist_path = sdists[0]
    assert sdist_path.is_file()

    session.log("Installing cocotb from sdist, which includes the build step")
    session.install(str(sdist_path))

    session.log("Running cocotb-config as basic installation smoke test")
    session.run("cocotb-config", "--version")


@nox.session
@nox.parametrize("sim,toplevel_lang,gpi_interface", simulator_support_matrix())
def release_test(
    session: nox.Session, sim: str, toplevel_lang: str, gpi_interface: str
) -> None:
    """Run all tests against a cocotb release installed from wheels."""
    session.install("--group", "release_test")
    release_install_wheel(session)
    release_test_nosim(session)
    release_test_sim(session, sim, toplevel_lang, gpi_interface)


def release_install_wheel(session: nox.Session) -> None:
    """Helper: Install cocotb from wheels and also install test dependencies."""

    wheels = list(Path(dist_dir).glob("cocotb-*.whl"))
    if not wheels:
        session.notify("release_build_wheel")
        wheels = list(Path(dist_dir).glob("cocotb-*.whl"))

    session.log(f"Installing cocotb from wheels in {dist_dir!r}")
    session.install(
        "--force-reinstall",
        "--only-binary",
        "cocotb",
        "--no-index",
        "--no-dependencies",
        "--find-links",
        dist_dir,
        "cocotb",
    )

    session.log("Running cocotb-config as basic installation smoke test")
    session.run("cocotb-config", "--version")


def release_test_sim(
    session: nox.Session, sim: str, toplevel_lang: str, gpi_interface: str
) -> None:
    """Test a release version of cocotb against a simulator."""

    env = env_vars_for_test(sim, toplevel_lang, gpi_interface)
    config_str = stringify_dict(env)

    if "COCOTB_CI_SKIP_MAKE" not in os.environ:
        session.log(f"Running tests against a simulator: {config_str}")
        session.run("make", "-k", "test", external=True, env=env)

    session.log(f"Running simulator-specific tests against a simulator {config_str}")
    session.run(
        "pytest",
        "-v",
        "-k",
        "simulator_required",
        env=env,
    )

    session.log(f"All tests passed with configuration {config_str}!")


def release_test_nosim(session: nox.Session) -> None:
    """Run the simulator-agnostic tests against a cocotb release."""

    session.log("Running simulator-agnostic tests")
    session.run(
        "pytest",
        "-v",
        "-k",
        "not simulator_required",
    )

    session.log("All tests passed!")


#
# Documentation sessions.
#


@nox.session
def docs(session: nox.Session) -> None:
    """invoke sphinx-build to build the HTML docs"""
    session.install("--group", "docs")
    session.install(".")
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build",
        "./docs/source",
        str(outdir),
        "--color",
        "-b",
        "html",
        *session.posargs,
    )
    index = (outdir / "index.html").resolve().as_uri()
    session.log(f"Documentation is available at {index}")


@nox.session
def docs_preview(session: nox.Session) -> None:
    """Build a live preview of the documentation"""
    session.install("--group", "docs-preview")
    # Editable install allows editing cocotb source and seeing it updated in the live preview
    session.install("-e", ".")
    outdir = session.cache_dir / "docs_out"
    # fmt: off
    session.run(
        "sphinx-autobuild",
        # Ignore directories which cause a rebuild loop.
        "--ignore", "*/source/master-notes.rst",
        "--ignore", "*/doxygen/*",
        # Ignore nox's venv directory.
        "--ignore", ".nox",
        # Ignore emacs backup files.
        "--ignore", "**/#*#",
        "--ignore", "**/.#*",
        # Ignore vi backup files.
        "--ignore", "**/.*.sw[px]",
        "--ignore", "**/*~",
        # FIXME: local to cmarqu :)
        "--ignore", "*@*:*",
        # Also watch the cocotb source directory to rebuild the API docs on
        # changes to cocotb code.
        "--watch", "src/cocotb",
        "./docs/source",
        str(outdir),
        *session.posargs,
    )
    # fmt: on


@nox.session
def docs_linkcheck(session: nox.Session) -> None:
    """invoke sphinx-build to linkcheck the docs"""
    session.install("--group", "docs")
    session.install(".")
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build",
        "./docs/source",
        str(outdir),
        "--color",
        "-b",
        "linkcheck",
        *session.posargs,
    )


@nox.session
def docs_spelling(session: nox.Session) -> None:
    """invoke sphinx-build to spellcheck the docs"""
    session.install("--group", "docs")
    session.install(".")
    outdir = session.cache_dir / "docs_out"
    session.run(
        "sphinx-build",
        "./docs/source",
        str(outdir),
        "--color",
        "-b",
        "spelling",
        *session.posargs,
    )
