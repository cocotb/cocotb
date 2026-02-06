# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test xUnit XML reporter."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from platform import node
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from cocotb._xunit_reporter import XUnitReporter


def test_empty_testsuite(tmp_path: Path) -> None:
    """xUnit XML report with empty testsuite."""
    results: Path = tmp_path / "results.xml"

    xunit: XUnitReporter = XUnitReporter(relative_to=tmp_path)
    xunit.write(results)

    assert results.exists()

    root: Element = ElementTree.parse(results).getroot()

    assert root.get("name")
    assert len(root.attrib) == 1
    assert len(root.findall("testsuite")) == 0


def test_report(tmp_path: Path) -> None:
    """xUnit XML report with mixed test results."""
    results: Path = tmp_path / "subdir" / "results.xml"

    attachments: tuple[Path, ...] = (
        tmp_path / "sim.log",
        tmp_path / "wave.vcd",
    )

    for attachment in attachments:
        attachment.touch(0o600, exist_ok=True)

    xunit: XUnitReporter = XUnitReporter(
        relative_to=tmp_path,
        # Common default properties that will be added to all created test cases
        default_properties={
            "cocotb": True,
            "random_seed": 100,
            "sim_time_duration": 0.0,
            "sim_time_unit": "ns",
            "sim_time_ratio": 0.0,
            "attachment": attachments,
        },
    )

    xunit.add_testcase(
        classname="package.module",
        name="test",
        status="passed",
        time=4.0,
        extra_properties={
            "sim_time_duration": 0.200,
            "sim_time_ratio": 2.0,
            "file": "module.py",
            "line": 10,
        },
    )

    xunit.add_testcase(
        classname="package.module",
        name="test",
        time=8.0,
        status="skipped",
        extra_properties={
            "sim_time_duration": 0.400,
            "sim_time_ratio": 4.0,
            "file": "module.py",
            "line": 12,
        },
    )

    xunit.add_testcase(
        classname="package.module",
        name="test",
        time=12.0,
        status="skipped",
        reason="Test skipped",
        extra_properties={
            "sim_time_duration": 0.800,
            "sim_time_ratio": 8.0,
            "file": "module.py",
            "line": 14,
        },
    )

    try:
        assert False, "Invalid value"
    except BaseException as e:
        xunit.add_testcase(
            classname="package.module",
            name="test",
            time=4.0,
            status="failed",
            reason=e,
            system_out="Test log",
            system_err="Test failed with COCOTB_RANDOM_SEED=100",
            extra_properties={
                "sim_time_duration": 0.400,
                "sim_time_ratio": 4.0,
                "file": "module.py",
                "line": 16,
            },
        )

    try:
        raise RuntimeError("Internal error")
    except BaseException as e:
        xunit.add_testcase(
            classname="package.module",
            name="test",
            time=4.0,
            status="error",
            reason=e,
            extra_properties={
                "file": "module.py",
                "line": 18,
            },
        )

    xunit.write(results)

    assert results.exists()

    root: Element = ElementTree.parse(results).getroot()

    assert root.get("name")
    assert len(root.attrib) == 1

    testsuites: Sequence[Element] = root.findall("testsuite")

    assert len(testsuites) == 1
    assert len(testsuites[0].attrib) == 8
    assert testsuites[0].find("properties") is None
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

    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    assert len(testcases) == 5
    assert len(testcases[0].attrib) == 3
    assert testcases[0].get("classname") == "package.module"
    assert testcases[0].get("name") == "test"
    assert testcases[0].get("time") == "4.000"
    assert len(testcases[0].findall("properties")) == 1

    # Testcase 0
    properties: list[Element] = (
        testcases[0].findall("properties")[0].findall("property")
    )

    assert len(properties) == 9
    assert len(properties[0].attrib) == 2
    assert properties[0].get("name") == "cocotb"
    assert properties[0].get("value") == "True"
    assert properties[1].get("name") == "random_seed"
    assert properties[1].get("value") == "100"
    assert properties[2].get("name") == "sim_time_duration"
    assert properties[2].get("value") == "0.2"
    assert properties[3].get("name") == "sim_time_unit"
    assert properties[3].get("value") == "ns"
    assert properties[4].get("name") == "sim_time_ratio"
    assert properties[4].get("value") == "2.0"
    assert properties[5].get("name") == "attachment"
    assert properties[5].get("value") == "sim.log"
    assert properties[6].get("name") == "attachment"
    assert properties[6].get("value") == "wave.vcd"
    assert properties[7].get("name") == "file"
    assert properties[7].get("value") == "module.py"
    assert properties[8].get("name") == "line"
    assert properties[8].get("value") == "10"

    assert len(testcases[0].findall("error")) == 0
    assert len(testcases[0].findall("failure")) == 0
    assert len(testcases[0].findall("skipped")) == 0
    assert len(testcases[0].findall("system-out")) == 1
    assert len(testcases[0].findall("system-err")) == 0

    # Testcase 1
    properties = testcases[1].findall("properties")[0].findall("property")

    assert len(properties) == 9
    assert len(testcases[1].findall("error")) == 0
    assert len(testcases[1].findall("failure")) == 0
    assert len(testcases[1].findall("skipped")) == 1
    assert len(testcases[1].findall("system-out")) == 1
    assert len(testcases[1].findall("system-err")) == 0

    skipped: Element = testcases[1].findall("skipped")[0]

    assert not skipped.attrib
    assert not skipped.text

    # Testcase 2
    properties = testcases[2].findall("properties")[0].findall("property")

    assert len(properties) == 9
    assert len(testcases[2].findall("error")) == 0
    assert len(testcases[2].findall("failure")) == 0
    assert len(testcases[2].findall("skipped")) == 1
    assert len(testcases[2].findall("system-out")) == 1
    assert len(testcases[2].findall("system-err")) == 0

    skipped = testcases[2].findall("skipped")[0]

    assert len(skipped.attrib) == 1
    assert skipped.get("message") == "Test skipped"
    assert not skipped.text

    # Testcase 3
    properties = testcases[3].findall("properties")[0].findall("property")

    assert len(properties) == 9
    assert len(testcases[3].findall("error")) == 0
    assert len(testcases[3].findall("failure")) == 1
    assert len(testcases[3].findall("skipped")) == 0
    assert len(testcases[3].findall("system-out")) == 1
    assert len(testcases[3].findall("system-err")) == 1

    failure: Element = testcases[3].findall("failure")[0]

    assert len(failure.attrib) == 2
    assert failure.get("message", "").splitlines() == ["Invalid value", "assert False"]
    assert failure.get("type") == "AssertionError"
    assert str(failure.text).startswith("Traceback (most recent call last):")

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

    assert len(properties) == 9
    assert len(testcases[4].findall("error")) == 1
    assert len(testcases[4].findall("failure")) == 0
    assert len(testcases[4].findall("skipped")) == 0
    assert len(testcases[4].findall("system-out")) == 1
    assert len(testcases[4].findall("system-err")) == 0


def test_file_outside_workspace(tmp_path: Path) -> None:
    """xUnit XML report where file is outside of workspace."""
    results: Path = tmp_path / "subdirA" / "results.xml"
    file: Path = tmp_path / "subdirB" / "module.py"

    file.parent.mkdir(0o700, parents=True, exist_ok=True)
    file.touch(0o600, exist_ok=True)

    xunit: XUnitReporter = XUnitReporter(relative_to=results.parent)

    xunit.add_testcase(
        name="test",
        classname="module",
        status="passed",
        extra_properties={
            "file": str(file),
            "attachment": file,
        },
    )

    xunit.write(results)

    root: Element = ElementTree.parse(results).getroot()
    testsuites: Sequence[Element] = root.findall("testsuite")
    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    properties: dict[str, str] = {
        item.get("name", ""): item.get("value", "")
        for item in testcases[0].iter("property")
    }

    assert properties["file"] == str(file)
    assert properties["attachment"] == str(file)

    assert str(testcases[0].findall("system-out")[0].text).splitlines() == [
        f"[[ATTACHMENT|{file}]]",
    ]


def test_without_attachments(tmp_path: Path) -> None:
    """xUnit XML report without attachments."""
    results: Path = tmp_path / "results.xml"

    xunit: XUnitReporter = XUnitReporter()

    xunit.add_testcase(
        name="test",
        classname="module",
        status="passed",
        extra_properties={
            "attachment": (),
        },
    )

    xunit.write(results)

    root: Element = ElementTree.parse(results).getroot()
    testsuites: Sequence[Element] = root.findall("testsuite")
    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    assert len(list(testcases[0].iter("property"))) == 0
    assert testcases[0].find("system-out") is None


def test_properties(tmp_path: Path) -> None:
    """xUnit XML report with properties."""
    results: Path = tmp_path / "results.xml"

    xunit: XUnitReporter = XUnitReporter(relative_to=tmp_path)

    xunit.add_testcase(
        name="test",
        classname="module",
        status="passed",
        extra_properties={
            "cocotb": True,
            "coverage": False,
            "file": results,
            "line": 10,
            "attachment": str(results),
            "sim_time_unit": "ns",
            "sim_time_ratio": 0.0,
            "sim_time_duration": 0,
            "list0": (),
            "list1": ("a",),
            "list2": ("a", "b"),
        },
    )

    xunit.write(results)

    root: Element = ElementTree.parse(results).getroot()
    testsuites: Sequence[Element] = root.findall("testsuite")
    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    assert len(list(testcases[0].iter("properties"))) == 1

    properties: dict[str, str] = {
        item.get("name", ""): item.get("value", "")
        for item in testcases[0].iter("property")
    }

    assert len(properties) == 10
    assert properties["cocotb"] == "True"
    assert properties["coverage"] == "False"
    assert properties["line"] == "10"
    assert properties["file"] == str(results.relative_to(tmp_path))
    assert properties["attachment"] == str(results.relative_to(tmp_path))
    assert properties["sim_time_unit"] == "ns"
    assert properties["sim_time_ratio"] == "0.0"
    assert properties["sim_time_duration"] == "0"
    assert properties["list1"] == "a"
    assert properties["list2"] == "b"


def test_invalid_characters(tmp_path: Path) -> None:
    """xUnit XML report with invalid characters."""
    results: Path = tmp_path / "results.xml"

    xunit: XUnitReporter = XUnitReporter()

    xunit.add_testcase(
        name="test",
        classname="module",
        status="passed",
        system_out="\uffff",
        system_err="\u001f",
    )

    xunit.write(results)

    root: Element = ElementTree.parse(results).getroot()
    testsuites: Sequence[Element] = root.findall("testsuite")
    testcases: Sequence[Element] = testsuites[0].findall("testcase")

    assert str(testcases[0].findall("system-out")[0].text).splitlines() == ["#xFFFF"]
    assert str(testcases[0].findall("system-err")[0].text).splitlines() == ["#x1F"]
