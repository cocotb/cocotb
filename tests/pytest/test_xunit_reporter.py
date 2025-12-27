# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test xUnit XML reporter."""

from __future__ import annotations

import os
from collections.abc import Generator, Sequence
from datetime import datetime, timezone
from pathlib import Path
from platform import node
from unittest import mock
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from pytest import MonkeyPatch, fixture

from cocotb._xunit_reporter import XUnitReporter


def test_empty_testsuite(tmp_path: Path) -> None:
    """xUnit XML report with empty testsuite."""
    results: Path = tmp_path / "results.xml"

    xunit: XUnitReporter = XUnitReporter(family="xunit2", workspace=tmp_path)
    xunit.write(results)

    assert results.exists()

    root: Element = ElementTree.parse(results).getroot()

    assert root.get("name")
    assert len(root.attrib) == 1
    assert len(root.findall("testsuite")) == 0


def test_report(tmp_path: Path) -> None:
    """xUnit XML report with mixed test results."""
    results: Path = tmp_path / "subdir" / "results.xml"

    (tmp_path / "sim.log").touch(0o600, exist_ok=True)
    (tmp_path / "wave.vcd").touch(0o600, exist_ok=True)

    xunit: XUnitReporter = XUnitReporter(
        family="xunit2",
        workspace=tmp_path,
        random_seed=100,
    )

    xunit.add_testcase(
        classname="package.module",
        name="test",
        file="module.py",
        line=10,
        time=4.0,
        sim_time_duration=0.400,
        sim_time_unit="ns",
        sim_time_ratio="4.0",
    )

    xunit.add_testcase(
        classname="package.module",
        name="test",
        file="module.py",
        line=12,
        time=8.0,
        sim_time_duration=0.400,
        sim_time_unit="ns",
        sim_time_ratio="4.0",
        skipped=True,
    )

    xunit.add_testcase(
        classname="package.module",
        name="test",
        file="module.py",
        line=14,
        time=12.0,
        sim_time_duration=0.400,
        sim_time_unit="ns",
        sim_time_ratio="4.0",
        skipped="Test skipped",
    )

    try:
        assert False, "Invalid value"
    except BaseException as e:
        xunit.add_testcase(
            classname="package.module",
            name="test",
            file="module.py",
            line=16,
            time=4.0,
            sim_time_duration=0.400,
            sim_time_unit="ns",
            sim_time_ratio="4.0",
            failure=e,
            attachments=(tmp_path / "sim.log", tmp_path / "wave.vcd"),
            system_out="Test log",
            system_err="Test failed with COCOTB_RANDOM_SEED=100",
        )

    try:
        raise RuntimeError("Internal error")
    except BaseException as e:
        xunit.add_testcase(
            classname="package.module",
            name="test",
            file="module.py",
            line=18,
            time=4.0,
            error=e,
            attachments=(tmp_path / "non-existing.log",),
        )

    xunit.write(results)

    assert results.exists()

    root: Element = ElementTree.parse(results).getroot()

    assert root.get("name")
    assert len(root.attrib) == 1

    testsuites: Sequence[Element] = root.findall("testsuite")

    assert len(testsuites) == 1
    assert len(testsuites[0].attrib) == 8
    assert len(testsuites[0].findall("properties")) == 1
    assert testsuites[0].get("name")
    assert testsuites[0].get("errors") == "1"
    assert testsuites[0].get("failures") == "1"
    assert testsuites[0].get("skipped") == "2"
    assert testsuites[0].get("tests") == "5"
    assert testsuites[0].get("time") == "32.000"
    assert testsuites[0].get("hostname") == node()
    assert (
        datetime.fromisoformat(testsuites[0].get("timestamp", "")).timestamp()
        <= datetime.now(timezone.utc).timestamp()
    )

    properties: list[Element] = (
        testsuites[0].findall("properties")[0].findall("property")
    )

    assert len(properties) == 1
    assert len(properties[0].attrib) == 2
    assert properties[0].get("name") == "random_seed"
    assert properties[0].get("value") == "100"

    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    assert len(testcases) == 5
    assert len(testcases[0].attrib) == 3
    assert testcases[0].get("classname") == "package.module"
    assert testcases[0].get("name") == "test"
    assert testcases[0].get("time") == "4.000"
    assert len(testcases[0].findall("properties")) == 1

    # Testcase 0
    properties = testcases[0].findall("properties")[0].findall("property")

    assert len(properties) == 5
    assert len(properties[0].attrib) == 2
    assert properties[0].get("name") == "file"
    assert properties[0].get("value") == "module.py"
    assert properties[1].get("name") == "line"
    assert properties[1].get("value") == "10"
    assert properties[2].get("name") == "sim_time_duration"
    assert properties[2].get("value") == "0.4"
    assert properties[3].get("name") == "sim_time_unit"
    assert properties[3].get("value") == "ns"
    assert properties[4].get("name") == "sim_time_ratio"
    assert properties[4].get("value") == "4.0"

    assert len(testcases[0].findall("error")) == 0
    assert len(testcases[0].findall("failure")) == 0
    assert len(testcases[0].findall("skipped")) == 0
    assert len(testcases[0].findall("system-out")) == 0
    assert len(testcases[0].findall("system-err")) == 0

    # Testcase 1
    properties = testcases[1].findall("properties")[0].findall("property")

    assert len(properties) == 5
    assert len(testcases[1].findall("error")) == 0
    assert len(testcases[1].findall("failure")) == 0
    assert len(testcases[1].findall("skipped")) == 1
    assert len(testcases[1].findall("system-out")) == 0
    assert len(testcases[1].findall("system-err")) == 0

    skipped: Element = testcases[1].findall("skipped")[0]

    assert not skipped.attrib
    assert not skipped.text

    # Testcase 2
    properties = testcases[2].findall("properties")[0].findall("property")

    assert len(properties) == 5
    assert len(testcases[2].findall("error")) == 0
    assert len(testcases[2].findall("failure")) == 0
    assert len(testcases[2].findall("skipped")) == 1
    assert len(testcases[2].findall("system-out")) == 0
    assert len(testcases[2].findall("system-err")) == 0

    skipped = testcases[2].findall("skipped")[0]

    assert len(skipped.attrib) == 1
    assert skipped.get("message") == "Test skipped"
    assert not skipped.text

    # Testcase 3
    properties = testcases[3].findall("properties")[0].findall("property")

    assert len(properties) == 7
    assert len(testcases[3].findall("error")) == 0
    assert len(testcases[3].findall("failure")) == 1
    assert len(testcases[3].findall("skipped")) == 0
    assert len(testcases[3].findall("system-out")) == 1
    assert len(testcases[3].findall("system-err")) == 1

    failure: Element = testcases[3].findall("failure")[0]

    assert len(failure.attrib) == 2
    assert failure.get("message") == "Invalid value"
    assert failure.get("type") == "AssertionError"
    assert str(failure.text).startswith("Traceback (most recent call last):")

    assert properties[5].get("name") == "attachment"
    assert properties[5].get("value") == "sim.log"
    assert properties[6].get("name") == "attachment"
    assert properties[6].get("value") == "wave.vcd"

    assert str(testcases[3].findall("system-out")[0].text).splitlines() == [
        "Test log",
        "[[ATTACHMENT|sim.log]]",
        "[[ATTACHMENT|wave.vcd]]",
    ]

    assert str(testcases[3].findall("system-err")[0].text).splitlines() == [
        "Test failed with COCOTB_RANDOM_SEED=100",
    ]

    # Testcase 4
    properties = testcases[4].findall("properties")[0].findall("property")

    assert len(properties) == 2
    assert len(testcases[4].findall("error")) == 1
    assert len(testcases[4].findall("failure")) == 0
    assert len(testcases[4].findall("skipped")) == 0
    assert len(testcases[4].findall("system-out")) == 0
    assert len(testcases[4].findall("system-err")) == 0


def test_legacy(tmp_path: Path) -> None:
    """xUnit XML report in legacy format (xunit1)."""
    results: Path = tmp_path / "results.xml"

    xunit: XUnitReporter = XUnitReporter(family="xunit1", workspace=tmp_path)

    xunit.add_testcase(
        classname="package.module",
        name="test",
        file="module.py",
        line=10,
        time=4.0,
        sim_time_duration=0.400,
        sim_time_unit="ns",
        sim_time_ratio="4.0",
    )

    xunit.write(results)

    assert results.exists()

    root: Element = ElementTree.parse(results).getroot()

    testsuites: Sequence[Element] = root.findall("testsuite")

    assert len(testsuites) == 1
    assert len(testsuites[0].attrib) == 8
    assert len(testsuites[0].findall("properties")) == 0
    assert testsuites[0].get("name")
    assert testsuites[0].get("errors") == "0"
    assert testsuites[0].get("failures") == "0"
    assert testsuites[0].get("skipped") == "0"
    assert testsuites[0].get("tests") == "1"
    assert testsuites[0].get("time") == "4.000"
    assert testsuites[0].get("hostname") == node()
    assert (
        datetime.fromisoformat(testsuites[0].get("timestamp", "")).timestamp()
        <= datetime.now(timezone.utc).timestamp()
    )

    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    assert len(testcases) == 1
    assert len(testcases[0].attrib) == 5
    assert testcases[0].get("classname") == "package.module"
    assert testcases[0].get("name") == "test"
    assert testcases[0].get("file") == "module.py"
    assert testcases[0].get("line") == "10"
    assert testcases[0].get("time") == "4.000"
    assert len(testcases[0].findall("properties")) == 1

    properties: list[Element] = (
        testcases[0].findall("properties")[0].findall("property")
    )

    assert len(properties) == 5
    assert len(properties[0].attrib) == 2
    assert properties[0].get("name") == "file"
    assert properties[0].get("value") == "module.py"
    assert properties[1].get("name") == "line"
    assert properties[1].get("value") == "10"
    assert properties[2].get("name") == "sim_time_duration"
    assert properties[2].get("value") == "0.4"
    assert properties[3].get("name") == "sim_time_unit"
    assert properties[3].get("value") == "ns"
    assert properties[4].get("name") == "sim_time_ratio"
    assert properties[4].get("value") == "4.0"

    assert len(testcases[0].findall("error")) == 0
    assert len(testcases[0].findall("failure")) == 0
    assert len(testcases[0].findall("skipped")) == 0
    assert len(testcases[0].findall("system-out")) == 0
    assert len(testcases[0].findall("system-err")) == 0


def test_file_outside_workspace(tmp_path: Path) -> None:
    """xUnit XML report where file is outside of workspace."""
    results: Path = tmp_path / "subdirA" / "results.xml"
    file: Path = tmp_path / "subdirB" / "module.py"

    file.parent.mkdir(0o700, parents=True, exist_ok=True)
    file.touch(0o600, exist_ok=True)

    xunit: XUnitReporter = XUnitReporter(family="xunit1", workspace=results.parent)

    xunit.add_testcase(
        classname="package.module",
        name="test",
        file=file,
        line=10,
        time=4.0,
    )

    xunit.write(results)

    root: Element = ElementTree.parse(results).getroot()
    testsuites: Sequence[Element] = root.findall("testsuite")
    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    assert testcases[0].get("file") == str(file)


def test_invalid_characters(tmp_path: Path) -> None:
    """xUnit XML report with invalid characters."""
    results: Path = tmp_path / "results.xml"

    xunit: XUnitReporter = XUnitReporter(family="xunit2", workspace=tmp_path)

    xunit.add_testcase(
        classname="package.module",
        name="test",
        file="module.py",
        line=10,
        time=4.0,
        system_out="\uffff",
        system_err="\u001f",
    )

    xunit.write(results)

    root: Element = ElementTree.parse(results).getroot()
    testsuites: Sequence[Element] = root.findall("testsuite")
    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    assert testcases[0].findall("system-out")[0].text == "#xFFFF"
    assert testcases[0].findall("system-err")[0].text == "#x1F"


@fixture(name="unknown_env")
def unknown_env_fixture(monkeypatch: MonkeyPatch) -> Generator[None, None, None]:
    """Unknown environment."""
    with mock.patch.dict(os.environ, clear=True):
        yield  # Restore environment variables


def test_unknown_env(unknown_env: None) -> None:
    """Text xUnit reporter in unknown environment."""
    xunit: XUnitReporter = XUnitReporter()

    assert xunit.environment is None
    assert xunit.workspace == Path.cwd()
    assert xunit.family == "xunit2"


@fixture(name="gitlab_env")
def gitlab_env_fixture(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> Generator[None, None, None]:
    """GitLab CI environment."""
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("GITLAB_CI", "true")
        monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))

        yield  # Restore environment variables


def test_gitlab_env(gitlab_env: None, tmp_path: Path) -> None:
    """Text xUnit reporter in GitLab CI environment."""
    xunit: XUnitReporter = XUnitReporter()

    assert xunit.environment == "gitlab"
    assert xunit.workspace == tmp_path
    assert xunit.family == "xunit1"


@fixture(name="github_env")
def github_env_fixture(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> Generator[None, None, None]:
    """GitHub Actions environment."""
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

        yield  # Restore environment variables


def test_github_env(github_env: None, tmp_path: Path) -> None:
    """Text xUnit reporter in GitHub Actions environment."""
    xunit: XUnitReporter = XUnitReporter()

    assert xunit.environment == "github"
    assert xunit.workspace == tmp_path
    assert xunit.family == "xunit2"


@fixture(name="jenkins_env")
def jenkins_env_fixture(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> Generator[None, None, None]:
    """Jenkins CI environment."""
    with mock.patch.dict(os.environ, clear=True):
        monkeypatch.setenv("BUILD_TAG", "jenkins-0")
        monkeypatch.setenv("WORKSPACE", str(tmp_path))

        yield  # Restore environment variables


def test_jenkins_env(jenkins_env: None, tmp_path: Path) -> None:
    """Text xUnit reporter in Jenkins CI environment."""
    xunit: XUnitReporter = XUnitReporter()

    assert xunit.environment == "jenkins"
    assert xunit.workspace == tmp_path
    assert xunit.family == "xunit2"
