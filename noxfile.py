# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import glob

import nox

test_deps = ["coverage", "pytest", "pytest-cov"]

dev_deps = [
    "black",
    "isort",
    "mypy",
    "pre-commit",
    "nox",
    "tox",
    "flake8",
    "clang-format",
]


@nox.session
def tests(session: nox.Session) -> None:
    """run cocotb regression suite"""
    session.env["CFLAGS"] = "-Werror -Wno-deprecated-declarations -g --coverage"
    session.env["COCOTB_LIBRARY_COVERAGE"] = "1"
    session.env["CXXFLAGS"] = "-Werror"
    session.env["LDFLAGS"] = "--coverage"
    session.install(*test_deps)
    session.install("-e", ".")
    session.run("pytest")
    session.run("make", "test", external=True)
    coverage_files = glob.glob("**/.coverage.cocotb", recursive=True)
    session.run("coverage", "combine", "--append", *coverage_files)


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
    session.install(*test_deps)
    session.install(*dev_deps)
    session.install("-e", ".")
    if session.posargs:
        session.run(*session.posargs, external=True)
