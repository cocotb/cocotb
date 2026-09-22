# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
from contextlib import suppress
from pathlib import Path
from typing import cast

import nox
import nox_uv
from packaging.version import InvalidVersion, Version

nox.options.default_venv_backend = "uv"

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
        ("ryusim", "verilog", "vpi"),
        ("verilator", "verilog", "vpi"),
    ]

    return standard + special


def env_vars_for_sim_test(
    sim: str, toplevel_lang: str, gpi_interface: str
) -> dict[str, str]:
    """Prepare the environment variables controlling the test run."""
    env = {
        "SIM": sim,
        "TOPLEVEL_LANG": toplevel_lang,
    }

    assert not (toplevel_lang == "verilog" and gpi_interface != "vpi")
    if toplevel_lang == "vhdl":
        env["VHDL_GPI_INTERFACE"] = gpi_interface

    return env


def configure_test_env(session: nox.Session) -> None:
    """Set environment variables for any kind of test run."""

    # Do not fail on DeprecationWarning caused by virtualenv, which might come from
    # the site module.
    session.env["PYTHONWARNINGS"] = (
        "error,ignore::DeprecationWarning:site,ignore:coroutine :RuntimeWarning"
    )

    # Test with debug enabled, but log level still set low. That way we can test the code
    # without slowing everything down by emitting roughly 1 million logs.
    session.env["COCOTB_SCHEDULER_DEBUG"] = "1"
    session.env["GPI_DEBUG"] = "1"
    session.env["PYGPI_DEBUG"] = "1"


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


@nox_uv.session(
    uv_groups=["dev_test"],
    uv_no_install_project=True,
    uv_sync_locked=False,
)
@nox.parametrize("sim,toplevel_lang,gpi_interface", simulator_support_matrix())
def dev_test(
    session: nox.Session,
    sim: str,
    toplevel_lang: str,
    gpi_interface: str,
) -> None:
    """Run all development tests and merge coverage."""
    build_cocotb_for_dev_test(session)
    configure_test_env(session)
    # Collect coverage of cocotb
    session.env["COCOTB_LIBRARY_COVERAGE"] = "1"
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

    env = env_vars_for_sim_test(sim, toplevel_lang, gpi_interface)
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
        make_args = ["make"]
        if "COCOTB_CI_FAIL_FAST" not in os.environ:
            make_args.append("-k")
        make_args.append("test")
        session.run(*make_args, external=True, env=env)

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
        "-s",
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
        "-s",
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
    for example in pytest_example_tree:
        with session.chdir(example):
            session.run(
                "pytest",
                "-s",
                "-v",
                env=env,
            )

    # We need to run it separately to avoid loading pytest cocotb plugin for other tests
    session.log(f"Running tests for pytest plugin against a simulator {config_str}")
    session.run(
        "pytest",
        "-s",
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
        "-s",
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


@nox_uv.session(
    uv_groups=["coverage_report"],
    uv_no_install_project=True,
    uv_sync_locked=False,
)
def dev_coverage_report(session: nox.Session) -> None:
    """Report coverage results."""

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


@nox_uv.session(
    uv_no_install_project=True,
    uv_groups=[],
    uv_sync_locked=False,
)
def release_clean(session: nox.Session) -> None:
    """Remove all build artifacts from the dist directory."""
    shutil.rmtree(dist_dir, ignore_errors=True)


@nox_uv.session(
    uv_no_install_project=True,
    uv_groups=["release_build_wheel"],
    uv_sync_locked=False,
)
def release_build_wheel(session: nox.Session) -> None:
    """Build a binary distribution (wheels) on the current operating system."""

    session.log("Building binary distributions (wheels)")
    session.run(
        "cibuildwheel",
        "--output-dir",
        dist_dir,
    )

    session.log(f"Binary distribution in release mode built into {dist_dir!r}")


@nox_uv.session(
    uv_no_install_project=True,
    uv_groups=["release_build_sdist"],
    uv_sync_locked=False,
)
def release_build_sdist(session: nox.Session) -> None:
    """Build the source distribution."""

    session.log("Building source distribution (sdist)")
    session.run("python", "-m", "build", "--sdist", "--outdir", dist_dir, ".")

    session.log(f"Source distribution in release mode built into {dist_dir!r}")


@nox_uv.session(
    uv_no_install_project=True,
    uv_groups=[],
    uv_sync_locked=False,
)
def release_build(session: nox.Session) -> None:
    """Build all distributions for release."""
    session.notify("release_build_wheel")
    session.notify("release_build_sdist")


def release_install_from_sdist(session: nox.Session) -> None:
    """Install cocotb from sdist."""

    # Find the sdist to install.
    sdists = list(Path(dist_dir).glob("cocotb-*.tar.gz"))
    if not sdists:
        session.error(
            f"No potential sdist found in the {dist_dir!r} directory. "
            f"Run the 'release_build_sdist' session first!"
        )
    elif len(sdists) > 1:
        session.error(
            f"More than one potential sdist found in the {dist_dir!r} "
            f"directory: {', '.join(str(p) for p in sdists)}. "
            f"Run the 'release_clean' session first!"
        )
    sdist_path = sdists[0]
    assert sdist_path.is_file()

    session.log("Installing cocotb from sdist, which includes the build step")
    session.install(str(sdist_path))


@nox_uv.session(
    uv_no_install_project=True,
    uv_groups=["release_test"],
    uv_sync_locked=False,
)
@nox.parametrize("sim,toplevel_lang,gpi_interface", simulator_support_matrix())
@nox.parametrize("source", ["wheel", "sdist"])
def release_test(
    session: nox.Session, sim: str, toplevel_lang: str, gpi_interface: str, source: str
) -> None:
    """Run all tests against a cocotb release build."""
    if source == "sdist":
        release_install_from_sdist(session)
    else:
        release_install_from_wheel(session)

    session.log("Running cocotb-config as basic installation smoke test")
    session.run("cocotb-config", "--version")
    configure_test_env(session)
    release_test_nosim(session)
    release_test_sim(session, sim, toplevel_lang, gpi_interface)


def release_install_from_wheel(session: nox.Session) -> None:
    """Install cocotb from wheels."""

    wheels = list(Path(dist_dir).glob("cocotb-*.whl"))
    if not wheels:
        session.error(
            f"No potential wheel found in the {dist_dir!r} directory. Run the 'release_build_wheel' session first!"
        )
    session.log(f"Installing cocotb from wheels in {dist_dir!r}")
    session.install(
        "--force-reinstall",
        "--only-binary",
        "cocotb",
        "--no-index",
        "--no-deps",
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

    env = env_vars_for_sim_test(sim, toplevel_lang, gpi_interface)
    config_str = stringify_dict(env)

    session.log(f"Running simulator-specific tests against a simulator {config_str}")
    session.run(
        "pytest",
        "-s",
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
        "-s",
        "-v",
        "-k",
        "not simulator_required",
    )

    session.log("All tests passed!")


#
# Documentation sessions.
#


@nox_uv.session(
    uv_groups=["docs"],
    uv_sync_locked=False,
)
def docs(session: nox.Session) -> None:
    """invoke sphinx-build to build the HTML docs"""
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


@nox_uv.session(
    uv_groups=["docs_preview"],
    uv_sync_locked=False,
)
def docs_preview(session: nox.Session) -> None:
    """Build a live preview of the documentation"""
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


@nox_uv.session(
    uv_groups=["docs"],
    uv_sync_locked=False,
)
def docs_linkcheck(session: nox.Session) -> None:
    """invoke sphinx-build to linkcheck the docs"""
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


@nox_uv.session(
    uv_groups=["docs"],
    uv_sync_locked=False,
)
def docs_spelling(session: nox.Session) -> None:
    """invoke sphinx-build to spellcheck the docs"""
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


# Everything below is shared by the "release_notes" and
# "backport_release_notes" sessions, and mirrors the towncrier settings in
# pyproject.toml.
RELEASE_NOTES = Path("docs") / "source" / "release_notes.rst"
NEWSFRAGMENTS = Path("docs") / "source" / "newsfragments"
# Names the version a branch is working towards, and hence the version its
# next release notes are filed under. See "cocotb Releases" in
# docs/source/maintaining.rst.
VERSION_FILE = Path("VERSION")
# Inserted by towncrier as the header of each release's section. Also the
# marker this file uses to find where a section starts and ends.
SECTION_HEADER_RE = re.compile(r"^cocotb (?P<version>\S+) \([^)]*\)$")
# Final releases only: X.Y.Z, no rc/b/a suffix.
FINAL_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _git(*args: str, check: bool = True) -> str:
    """Run a git command and return its stdout."""
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=check
    ).stdout


def _section_starts(lines: list[str]) -> list[tuple[int, str]]:
    """Return the ``(line number, version)`` of every release notes section."""
    return [
        (i, m.group("version"))
        for i, line in enumerate(lines)
        if (m := SECTION_HEADER_RE.match(line))
        # A header is always underlined with '=' (see pyproject.toml).
        and i + 1 < len(lines)
        and set(lines[i + 1]) == {"="}
    ]


def _find_section(lines: list[str], version: str) -> tuple[int, int] | None:
    """Return the ``[start, end)`` line range of a version's release notes."""
    starts = _section_starts(lines)
    for index, (start, found) in enumerate(starts):
        if found == version:
            end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
            return start, end
    return None


@nox_uv.session(
    # towncrier only needs its config and the newsfragments; it is told the
    # project name and version explicitly, so there is no need to build and
    # install cocotb itself here.
    uv_no_install_project=True,
    uv_groups=["docs"],
    uv_sync_locked=False,
)
def release_notes(session: nox.Session) -> None:
    """Consume towncrier newsfragments into docs/source/release_notes.rst.

    The version to file them under is read from the VERSION file, which
    names the release the current branch is working towards. Pass
    ``--version`` to assert it is the expected one, e.g.
    ``nox -s release_notes -- --version=1.6.1``.

    Release notes are always filed under the final version, never under a
    release candidate: an rc is tagged from the very notes that the final
    release will ship, so this session is run once per release, before the
    first rc. Anything that lands on the release branch after an rc has to
    be folded into that existing section by hand (and its newsfragment
    deleted), which is also why re-running this session for a version that
    already has a section is refused rather than silently appending a
    second one.
    """
    parser = argparse.ArgumentParser(prog="nox -s release_notes --")
    parser.add_argument(
        "--version",
        help="Version to file the notes under. Must match the VERSION file.",
    )
    args, towncrier_args = parser.parse_known_args(session.posargs)

    version = VERSION_FILE.read_text().strip()
    if args.version is not None and args.version != version:
        session.error(
            f"{VERSION_FILE} says the current branch is working towards "
            f"{version}, not {args.version!r}. Release notes are filed under "
            "the version the branch is on, so bump the VERSION file first if "
            "that is wrong."
        )

    if not FINAL_VERSION_RE.match(version):
        session.error(
            f"{VERSION_FILE} contains {version!r}, which is not a final X.Y.Z "
            "version. Release notes are filed under the version being "
            "released, not under a release candidate: run this session once "
            "with the final version in place, then tag the rc from the "
            "resulting notes."
        )

    if _find_section(RELEASE_NOTES.read_text().splitlines(), version):
        session.error(
            f"{RELEASE_NOTES} already has a section for {version}. To add "
            "changes that landed after it was generated, edit that section by "
            f"hand and delete the newsfragments it covers from {NEWSFRAGMENTS}."
        )

    session.run(
        "towncrier",
        "build",
        "--yes",
        f"--version={version}",
        *towncrier_args,
    )


@nox_uv.session(
    uv_no_install_project=True,
    uv_groups=[],
    uv_sync_locked=False,
)
def backport_release_notes(session: nox.Session) -> None:
    """Copy a release's notes onto the currently checked out branch
    (normally master), without committing.

    towncrier only ever runs on a release branch (patch releases aren't
    made from master), but master's release notes should show the full
    history. This takes the finished section for the release — including
    any hand-edits made while reviewing it — out of ``--until``'s
    docs/source/release_notes.rst, inserts it here in version order, and
    deletes the newsfragments the release consumed so they aren't listed
    again under the next release.

    The section is inserted by version rather than always at the top,
    because a patch release on an older series can well be published after
    a newer series' first release: master's notes may already start with
    2.1.0 when 2.0.2's notes are backported.

    Pass the tag the release was made at with ``--until``, e.g.
    ``nox -s backport_release_notes -- --until=v1.6.1``. The notes section
    to copy is the one for that tag's version, ignoring any rc suffix
    (rcs ship the final release's notes); override with ``--version`` if
    it is named differently.

    Which newsfragments the release consumed is determined from the
    commits between ``--since`` and ``--until``. ``--since`` defaults to
    the point where the release branch forked from master, which covers
    every release made on the branch; fragments that an earlier one
    consumed are already gone from master, so only this release's are
    removed. Pass ``--since`` to narrow that down.
    """
    parser = argparse.ArgumentParser(prog="nox -s backport_release_notes --")
    parser.add_argument("--until", required=True)
    parser.add_argument("--since")
    parser.add_argument(
        "--version",
        help="Version whose notes section to copy. Default: derived from --until.",
    )
    args = parser.parse_args(session.posargs)

    if subprocess.run(
        ["git", "rev-parse", "--verify", args.until],
        capture_output=True,
        check=False,
    ).returncode:
        session.error(
            f"{args.until!r} is not a ref in this repository. If this is a CI "
            "checkout, make sure tags are fetched (fetch-depth: 0)."
        )

    # Uncommitted changes to the files this session rewrites would be
    # silently folded into the result, so refuse them. Anything else in the
    # working tree is none of this session's business and is left alone.
    if _git(
        "status",
        "--porcelain",
        "--",
        RELEASE_NOTES.as_posix(),
        NEWSFRAGMENTS.as_posix(),
    ).strip():
        session.error(
            f"{RELEASE_NOTES} and/or {NEWSFRAGMENTS} have uncommitted changes. "
            "Commit or stash them first."
        )

    version = args.version
    if version is None:
        # Release notes are filed under the final version, so drop any rc
        # suffix: the notes for v1.6.0rc1 are the "cocotb 1.6.0" section.
        match = re.match(r"^v?(?P<version>\d+\.\d+\.\d+)", args.until)
        if match is None:
            session.error(
                f"Can't tell which version {args.until!r} released. Pass "
                "--version explicitly."
            )
        version = match.group("version")

    since = args.since
    if since is None:
        # Everything this branch consumed since it diverged from master.
        #
        # The previous release tag would be a tighter boundary, but it is
        # the wrong one: a release candidate is tagged on the very notes
        # the final release ships, so for vX.Y.Z the previous tag is
        # vX.Y.ZrcN, which sits *after* the commit that consumed the
        # newsfragments. Widening the range to the fork point costs
        # nothing, because fragments an earlier release on this branch
        # consumed were removed from master by that release's own
        # backport, and only fragments still present here are deleted.
        #
        # In a CI checkout master is a local branch, but locally it can be
        # stale or missing entirely, so prefer the remote-tracking ref.
        master = "master"
        if not subprocess.run(
            ["git", "rev-parse", "--verify", "origin/master"],
            capture_output=True,
            check=False,
        ).returncode:
            master = "origin/master"

        since = subprocess.run(
            ["git", "merge-base", args.until, master],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    session.log(f"Backporting the {version} release notes from {args.until}.")

    released_lines = _git(
        "show", f"{args.until}:{RELEASE_NOTES.as_posix()}"
    ).splitlines()
    bounds = _find_section(released_lines, version)
    if bounds is None:
        session.error(
            f"{args.until} has no 'cocotb {version} (...)' section in "
            f"{RELEASE_NOTES}. Pass --version if the section is named "
            "differently."
        )
    section = "\n".join(released_lines[bounds[0] : bounds[1]]).rstrip("\n")

    lines = RELEASE_NOTES.read_text().splitlines()
    if _find_section(lines, version):
        session.error(
            f"{RELEASE_NOTES} already has a section for {version} here — "
            "these release notes have been backported already."
        )

    # Insert ahead of the first older release, so that backporting a patch
    # release of an older series doesn't put it above a newer one.
    existing = _section_starts(lines)
    insert_at = len(lines)
    for start, other in existing:
        try:
            is_older = Version(other) < Version(version)
        except InvalidVersion:
            continue
        if is_older:
            insert_at = start
            break
    else:
        if existing:
            session.log(
                f"{version} is older than every release listed in "
                f"{RELEASE_NOTES}; appending it at the end."
            )

    lines[insert_at:insert_at] = [*section.splitlines(), "", ""]
    RELEASE_NOTES.write_text("\n".join(lines).rstrip("\n") + "\n")
    _git("add", "--", RELEASE_NOTES.as_posix())

    # Every newsfragment the release consumed was deleted somewhere between
    # `since` and `until` — either by towncrier, or by hand while folding a
    # late change into the notes. Whatever of those still exists here (it
    # was added to master first, then backported to the release branch)
    # is now covered by the section just inserted.
    consumed = dict.fromkeys(
        _git(
            "log",
            "--format=",
            "--diff-filter=D",
            "--name-only",
            f"{since}..{args.until}",
            "--",
            NEWSFRAGMENTS.as_posix(),
        ).split()
    )
    stale = [fragment for fragment in consumed if Path(fragment).exists()]
    if stale:
        _git("rm", "--quiet", "--", *stale)
    session.log(
        f"Inserted the {version} notes and removed {len(stale)} of "
        f"{len(consumed)} consumed newsfragment(s)."
    )
