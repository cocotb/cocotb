# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import glob
import os
import shutil
from collections.abc import Iterable
from contextlib import suppress
from functools import cache
from pathlib import Path

from invoke import Collection, Context, task  # type: ignore[attr-defined]

#
# Helpers for use within this file.
#


@cache
def _simulator_support_matrix() -> tuple[tuple[str, str, str], ...]:
    """Get a list of supported simulator/toplevel-language/GPI-interface tuples."""

    # Simulators with support for VHDL through VHPI, and Verilog through VPI.
    standard = tuple(
        (sim, toplevel_lang, gpi_interface)
        for sim in ("activehdl", "riviera", "xcelium", "vcs", "questa")
        for toplevel_lang, gpi_interface in (("verilog", "vpi"), ("vhdl", "vhpi"))
    )

    # Special-case simulators.
    special = (
        ("cvc", "verilog", "vpi"),
        ("dsim", "verilog", "vpi"),
        ("ghdl", "vhdl", "vpi"),
        ("icarus", "verilog", "vpi"),
        ("nvc", "vhdl", "vhpi"),
        ("questa", "vhdl", "fli"),
        ("verilator", "verilog", "vpi"),
    )

    return standard + special


def _generate_tests(
    sim: str | None, toplevel_lang: str | None, gpi_interface: str | None
) -> Iterable[tuple[str, str, str]]:
    """Generate a list of test configurations based on the provided parameters.

    If any parameter is the empty string or ``None``,
    it is treated as a wildcard and all supported values for that parameter are included.
    """
    sims = sim.split(",") if sim else None
    toplevel_langs = toplevel_lang.split() if toplevel_lang else None
    gpi_interfaces = gpi_interface.split() if gpi_interface else None
    generated_one: bool = False
    for s, t, i in _simulator_support_matrix():
        if sims and s not in sims:
            continue
        if toplevel_langs and t not in toplevel_langs:
            continue
        if gpi_interfaces and i not in gpi_interfaces:
            continue
        yield s, t, i
        generated_one = True
    if not generated_one:
        raise ValueError(
            f"No supported simulator configuration found for sim={sim}, "
            f"toplevel_lang={toplevel_lang}, gpi_interface={gpi_interface}."
        )


def _env_vars_for_test(
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


def _stringify_dict(d: dict[str, str]) -> str:
    return ", ".join(f"{k}={v}" for k, v in d.items())


#
# Development pipeline
#
# - Use invoke to build an sdist; no separate build step is required.
# - Run tests against the installed sdist.
# - Collect coverage.
#


def _configure_env_for_dev_test() -> dict[str, str]:
    """Set environment variables for a development test.

    - Enable coverage collection.
    """
    # Collect coverage of cocotb
    return {"COCOTB_LIBRARY_COVERAGE": "1"}


@task
def dev_build(c: Context, *, editable: bool = True) -> None:
    """Build local cocotb for a development test.

    - Build with more aggressive error checking.
    """

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
    env = {
        "CFLAGS": flags,
        "CXXFLAGS": flags,
        "LDFLAGS": "--coverage",
    }

    if editable:
        c.run("pip install -v -e .", env=env)
    else:
        c.run("pip install -v .", env=env)


@task
def dev_test_sim(
    c: Context,
    *,
    sim: str | None = None,
    toplevel_lang: str | None = None,
    gpi_interface: str | None = None,
) -> None:
    """Test a development version of cocotb against a simulator.

    Omitting any of the parameters results in testing all supported values for that parameter.
    For example, running ``invoke dev-test-sim --sim=icarus`` will run tests for all
    supported GPI interfaces and top-level languages on Icarus Verilog.

    Args:
        sim: Simulator name (e.g., "icarus", "verilator")
        toplevel_lang: Top-level language ("verilog" or "vhdl")
        gpi_interface: GPI interface ("vpi", "vhpi", or "fli")
    """

    c.run("pip install --group test --group test_coverage")

    # Editable installs break C/C++ coverage collection; don't use them.
    # C/C++ coverage collection requires that the object files produced by the
    # compiler are not moved around, otherwise the gcno and gcda files produced
    # at compile and runtime, respectively, are located in the wrong
    # directories. Depending on the version of the Python install machinery
    # editable builds are done in a directory in /tmp, which is removed after
    # the build completes, taking all gcno files with them, as well as the path
    # to place the gcda files.
    dev_build(c, editable=False)

    for _sim, _toplevel_lang, _gpi_interface in _generate_tests(
        sim, toplevel_lang, gpi_interface
    ):
        _dev_test_sim_single(c, _sim, _toplevel_lang, _gpi_interface)


def _dev_test_sim_single(
    c: Context, sim: str, toplevel_lang: str, gpi_interface: str
) -> None:
    """Run tests for a single simulator configuration (sim, toplevel lang, gpi interface)."""

    dev_env = _configure_env_for_dev_test()

    env = {
        **os.environ.copy(),
        **dev_env,
        **_env_vars_for_test(sim, toplevel_lang, gpi_interface),
    }
    config_str = _stringify_dict(_env_vars_for_test(sim, toplevel_lang, gpi_interface))

    # Remove a potentially existing coverage file from a previous run for the
    # same test configuration. Use a filename *not* starting with `.coverage.`,
    # as coverage.py assumes ownership over these files and deleted them at
    # will.
    coverage_file = Path(f".cov.test.sim-{sim}-{toplevel_lang}-{gpi_interface}")
    with suppress(FileNotFoundError):
        coverage_file.unlink()

    if "COCOTB_CI_SKIP_MAKE" not in os.environ:
        print(f"Running `make test` against a simulator {config_str}")
        c.run("make -k test", env=env)

    # Run pytest for files which can only be tested in the source tree, not in
    # the installed binary (otherwise we get an "import file mismatch" error
    # from pytest).
    # TODO move this to dev_test_nosim once we can import cocotb files without
    # building the simulator module.
    print("Running simulator-agnostic tests in the source tree with pytest")

    result = c.run(
        'python -c "import cocotb; print(cocotb.__file__)"',
        env={"PYTHONWARNINGS": "ignore"},
        hide=True,
    )
    assert result is not None and result.ok
    cocotb_pkg_dir = Path(result.stdout.strip()).parent

    pytest_sourcetree = [
        str(cocotb_pkg_dir / "types"),
    ]
    c.run(
        f"pytest -v --doctest-modules --cov=cocotb --cov-branch --cov-report= --cov-append {' '.join(pytest_sourcetree)}"
    )

    print(f"Running simulator-specific tests against a simulator {config_str}")
    c.run(
        "pytest -v --cov=cocotb --cov-branch --cov-report= -k simulator_required",
        env=env,
    )
    Path(".coverage").rename(".coverage.pytest")

    print(f"Running examples against a simulator {config_str}")
    pytest_example_tree = [
        "examples/adder",
        "examples/simple_dff",
        "examples/matrix_multiplier",
        "examples/mixed_language",
    ]
    c.run(
        f"pytest -v {' '.join(pytest_example_tree)}",
        env=env,
    )

    # We need to run it separately to avoid loading pytest cocotb plugin for other tests
    print(f"Running tests for pytest plugin against a simulator {config_str}")
    c.run(
        f"pytest -v tests/pytest_plugin --cocotb-simulator {sim} "
        f"--cocotb-gpi-interfaces {gpi_interface} --cocotb-toplevel-lang {toplevel_lang}",
        env=env,
    )

    print(f"All tests and examples passed with configuration {config_str}!")

    # Combine coverage produced during the test runs, and place it in a file
    # with a name specific to this invocation of dev_test_sim().
    coverage_files = glob.glob("**/.coverage.cocotb", recursive=True)
    if not coverage_files:
        raise RuntimeError(
            "No coverage files found. Something went wrong during the test execution."
        )
    coverage_files.append(".coverage.pytest")
    c.run(f"coverage combine --append {' '.join(coverage_files)}")
    Path(".coverage").rename(coverage_file)

    print(f"Stored Python coverage for this test run in {coverage_file}.")


@task
def dev_test_nosim(c: Context) -> None:
    """Run the simulator-agnostic tests against a cocotb development version."""

    dev_env = _configure_env_for_dev_test()

    c.run("pip install --group test --group test_coverage")
    dev_build(c, editable=False)

    # Remove a potentially existing coverage file from a previous run for the
    # same test configuration. Use a filename *not* starting with `.coverage.`,
    # as coverage.py assumes ownership over these files and deleted them at
    # will.
    coverage_file = Path(".cov.test.nosim")
    with suppress(FileNotFoundError):
        coverage_file.unlink()

    # Run pytest with the default configuration in setup.cfg.
    print("Running simulator-agnostic tests with pytest")
    env = {**os.environ.copy(), **dev_env}
    c.run(
        "pytest -v --cov=cocotb --cov-branch --cov-report= -k 'not simulator_required'",
        env=env,
    )

    print("All tests passed!")

    # Rename the .coverage file to make it unique to the session.
    Path(".coverage").rename(coverage_file)

    print(f"Stored Python coverage for this test run in {coverage_file}.")


@task
def dev_coverage_combine(c: Context, gcov_executable: str | None = None) -> None:
    """Combine coverage from previous ``dev_*`` runs into a ``.coverage`` file.

    Args:
        gcov_executable: The path to the gcov executable to use for C++ code coverage.
    """
    c.run("pip install --group coverage_report")

    coverage_files = glob.glob("**/.cov.test.*", recursive=True)
    c.run(f"coverage combine {' '.join(coverage_files)}")
    assert Path(".coverage").is_file()

    print("Wrote combined coverage database for all tests to `.coverage`.")

    dev_coverage_report(c, gcov_executable=gcov_executable)


@task
def dev_coverage_report(c: Context, gcov_executable: str | None = None) -> None:
    """Report coverage results."""
    c.run("pip install --group coverage_report")

    # Produce Cobertura XML coverage reports.
    print("Producing Python and C/C++ coverage in Cobertura XML format")

    coverage_python_xml = Path(".python_coverage.xml")
    c.run(f"coverage xml -o {coverage_python_xml}")
    assert coverage_python_xml.is_file()

    gcov_executable_args = []
    if gcov_executable:
        gcov_executable_args = [
            "--gcov-executable",
            gcov_executable,
        ]

    coverage_cpp_xml = Path(".cpp_coverage.xml")
    c.run(
        f"gcovr --cobertura --output {coverage_cpp_xml} . {' '.join(gcov_executable_args)}"
    )
    assert coverage_cpp_xml.is_file()

    print(
        f"Cobertura XML files written to {str(coverage_cpp_xml)!r} (C/C++) and {str(coverage_python_xml)!r} (Python)"
    )

    # Report human-readable coverage.
    print("Python coverage")
    c.run("coverage report")

    print("Library coverage")
    c.run(f"gcovr --print-summary --txt {' '.join(gcov_executable_args)}")


@task
def dev_test(
    c: Context,
    *,
    sim: str | None = None,
    toplevel_lang: str | None = None,
    gpi_interface: str | None = None,
) -> None:
    """Run all tests, including those that don't need a simulator, and combine collected coverage.

    Omitting any of the parameters results in testing all supported values for that parameter.
    For example, running ``invoke dev-test-sim --sim=icarus`` will run tests for all
    supported GPI interfaces and top-level languages on Icarus Verilog.

    Args:
        sim: Simulator name (e.g., "icarus", "verilator")
        toplevel_lang: Top-level language ("verilog" or "vhdl")
        gpi_interface: GPI interface ("vpi", "vhpi", or "fli")
    """
    dev_test_nosim(c)
    dev_test_sim(c, sim=sim, toplevel_lang=toplevel_lang, gpi_interface=gpi_interface)
    dev_coverage_combine(c)


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


@task
def release_clean(c: Context) -> None:
    """Remove all build artifacts from the dist directory."""
    shutil.rmtree(dist_dir, ignore_errors=True)


@task
def release_build_bdist(c: Context) -> None:
    """Build a binary distribution (wheels) on the current operating system."""

    # Pin a version to ensure reproducible builds.
    c.run("pip install --group release_build")

    print("Building binary distribution (wheels)")
    c.run(f"cibuildwheel --output-dir {dist_dir}")

    print(f"Binary distribution in release mode built into {dist_dir!r}")


@task
def release_build_sdist(c: Context) -> None:
    """Build the source distribution."""

    c.run("pip install --group release_build_sdist")

    print("Building source distribution (sdist)")
    c.run(f"python -m build --sdist --outdir {dist_dir} .")

    print(f"Source distribution in release mode built into {dist_dir!r}")


@task(pre=[release_build_bdist, release_build_sdist])
def release_build(c: Context) -> None:
    """Build a release (sdist and bdist)."""
    pass


@task
def release_test_sdist(c: Context) -> None:
    """Build and install the sdist."""

    # Find the sdist to install.
    sdists = list(Path(dist_dir).glob("cocotb-*.tar.gz"))
    if len(sdists) == 0:
        raise RuntimeError(
            f"No *.tar.gz sdist file found in {dist_dir!r} "
            f"Run the `release-build` task first."
        )
    if len(sdists) > 1:
        raise RuntimeError(
            f"More than one potential sdist found in the {dist_dir!r} "
            f"directory. Run the `release-clean` task first!"
        )
    sdist_path = sdists[0]
    assert sdist_path.is_file()

    print("Installing cocotb from sdist, which includes the build step")
    c.run(f"pip install {sdist_path}")

    print("Running cocotb-config as basic installation smoke test")
    c.run("cocotb-config --version")


def _release_install(c: Context) -> None:
    """Helper: Install cocotb from wheels and also install test dependencies."""

    # We have to disable the use of the PyPi index when installing cocotb to
    # guarantee that the wheels in dist are being used. But without an index
    # pip cannot find the dependencies, which need to be installed from PyPi.
    # Work around that by explicitly installing the dependencies first from
    # PyPi, and then installing cocotb itself from the local dist directory.

    print("Installing cocotb dependencies from PyPi")
    c.run("pip install --group package_deps")

    print(f"Installing cocotb from wheels in {dist_dir!r}")
    c.run(
        f"pip install --force-reinstall --only-binary cocotb --no-index "
        f"--no-dependencies --find-links {dist_dir} cocotb"
    )

    print("Running cocotb-config as basic installation smoke test")
    c.run("cocotb-config --version")

    print("Installing test dependencies")
    c.run("pip install --group test")


@task
def release_test_sim(
    c: Context,
    *,
    sim: str | None = None,
    toplevel_lang: str | None = None,
    gpi_interface: str | None = None,
) -> None:
    """Test a release version of cocotb against a simulator.

    Args:
        sim: Simulator name (e.g., "icarus", "verilator")
        toplevel_lang: Top-level language ("verilog" or "vhdl")
        gpi_interface: GPI interface ("vpi", "vhpi", or "fli")
    """
    _release_install(c)
    for _sim, _toplevel_lang, _gpi_interface in _generate_tests(
        sim, toplevel_lang, gpi_interface
    ):
        _release_test_sim_single(c, _sim, _toplevel_lang, _gpi_interface)


def _release_test_sim_single(
    c: Context,
    sim: str,
    toplevel_lang: str,
    gpi_interface: str,
) -> None:
    """Run tests for a single simulator configuration (sim, toplevel lang, gpi interface)."""

    env = {**os.environ.copy(), **_env_vars_for_test(sim, toplevel_lang, gpi_interface)}
    config_str = _stringify_dict(_env_vars_for_test(sim, toplevel_lang, gpi_interface))

    if "COCOTB_CI_SKIP_MAKE" not in os.environ:
        print(f"Running tests against a simulator: {config_str}")
        c.run("make -k test", env=env)

    print(f"Running simulator-specific tests against a simulator {config_str}")
    c.run(
        "pytest -v -k simulator_required",
        env=env,
    )

    print(f"All tests passed with configuration {config_str}!")


@task
def release_test_nosim(c: Context) -> None:
    """Run the simulator-agnostic tests against a cocotb release."""

    _release_install(c)

    print("Running simulator-agnostic tests")
    c.run(
        "pytest -v -k 'not simulator_required'",
    )

    print("All tests passed!")


@task
def release_test(
    c: Context,
    *,
    sim: str | None = None,
    toplevel_lang: str | None = None,
    gpi_interface: str | None = None,
) -> None:
    """Run all tests, including those that don't need a simulator, against the release install.

    Omitting any of the parameters results in testing all supported values for that parameter.
    For example, running ``invoke dev-test-sim --sim=icarus`` will run tests for all
    supported GPI interfaces and top-level languages on Icarus Verilog.

    Args:
        sim: Simulator name (e.g., "icarus", "verilator")
        toplevel_lang: Top-level language ("verilog" or "vhdl")
        gpi_interface: GPI interface ("vpi", "vhpi", or "fli")
    """
    release_test_nosim(c)
    release_test_sim(
        c, sim=sim, toplevel_lang=toplevel_lang, gpi_interface=gpi_interface
    )


def _create_env_for_docs_build(c: Context) -> None:
    c.run("pip install --group docs")


@task
def docs(c: Context) -> None:
    """Run ``sphinx-build`` to build the HTML docs."""
    _create_env_for_docs_build(c)
    c.run("pip install .")

    outdir = Path(".docs_out")
    outdir.mkdir(parents=True, exist_ok=True)

    c.run(f"sphinx-build ./docs/source {outdir} --color -b html")
    index = (outdir / "index.html").resolve().as_uri()
    print(f"Documentation is available at {index}")


@task
def docs_preview(c: Context) -> None:
    """Build a live preview of the documentation."""
    _create_env_for_docs_build(c)
    # Editable install allows editing cocotb source and seeing it updated in the live preview
    c.run("pip install -e .")
    c.run("pip install sphinx-autobuild")

    outdir = Path(".docs_out")
    outdir.mkdir(parents=True, exist_ok=True)

    c.run(
        f"sphinx-autobuild "
        f"--ignore '*/source/master-notes.rst' "
        f"--ignore '*/doxygen/*' "
        f"--ignore '**/#*#' "
        f"--ignore '**/.#*' "
        f"--ignore '**/.*.sw[px]' "
        f"--ignore '**/*~' "
        f"--ignore '*@*:*' "
        f"--watch src/cocotb "
        f"./docs/source {outdir}"
    )


@task
def docs_linkcheck(c: Context) -> None:
    """Run ``sphinx-build`` to linkcheck the docs."""
    _create_env_for_docs_build(c)
    c.run("pip install .")

    outdir = Path(".docs_out")
    outdir.mkdir(parents=True, exist_ok=True)

    c.run(f"sphinx-build ./docs/source {outdir} --color -b linkcheck")


@task
def docs_spelling(c: Context) -> None:
    """Run ``sphinx-build`` to spellcheck the docs."""
    _create_env_for_docs_build(c)
    c.run("pip install .")

    outdir = Path(".docs_out")
    outdir.mkdir(parents=True, exist_ok=True)

    c.run(f"sphinx-build ./docs/source {outdir} --color -b spelling")


# Define the namespace
ns = Collection()

# Development tasks
dev = Collection("dev")
dev.add_task(dev_build, "build")
dev.add_task(dev_test, "test")
dev.add_task(dev_test_sim, "test-sim")
dev.add_task(dev_test_nosim, "test-nosim")
dev.add_task(dev_coverage_combine, "coverage-combine")
dev.add_task(dev_coverage_report, "coverage-report")
ns.add_collection(dev)

# Release tasks
release = Collection("release")
release.add_task(release_clean, "clean")
release.add_task(release_build, "build")
release.add_task(release_build_bdist, "build-bdist")
release.add_task(release_build_sdist, "build-sdist")
release.add_task(release_test_sdist, "test-sdist")
release.add_task(release_test, "test")
release.add_task(release_test_sim, "test-sim")
release.add_task(release_test_nosim, "test-nosim")
ns.add_collection(release)

# Documentation tasks
docs_collection = Collection("docs")
docs_collection.add_task(docs, "build")
docs_collection.add_task(docs_preview, "preview")
docs_collection.add_task(docs_linkcheck, "linkcheck")
docs_collection.add_task(docs_spelling, "spelling")
ns.add_collection(docs_collection)
