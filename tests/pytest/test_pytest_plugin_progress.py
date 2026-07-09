# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Regression tests for the cocotb pytest plugin's terminal progress reporting.

These tests exercise :mod:`cocotb_tools._pytest.plugin`'s collection logic in
isolation, using pytest's built-in ``pytester`` fixture instead of a real HDL
simulator. They do not run any cocotb test for real (no ``dut`` fixture is
available); they only check what pytest's collection machinery records, which
is what drives the built-in terminal progress bar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.pytester import Pytester

PLUGIN = "cocotb_tools._pytest.plugin"

# A single cocotb runner with three cocotb tests bound to it. Only the runner
# becomes a real pytest item during a normal (non ``--collect-only``) run; the
# three cocotb tests are instead reported later over IPC from the simulator
# subprocess (see ``Controller._handle_test_reports``). Regardless, all four
# still produce a test report and should count towards the pytest session's
# collected-test total, or the built-in progress bar overshoots 100% (#5303).
_TESTBENCH_SOURCE = """
    import pytest

    @pytest.mark.cocotb_runner
    def test_my_runner():
        pass

    @pytest.mark.cocotb_test
    async def test_thing_one(dut):
        pass

    @pytest.mark.cocotb_test
    async def test_thing_two(dut):
        pass

    @pytest.mark.cocotb_test
    async def test_thing_three(dut):
        pass
"""

# Printed from a conftest-level ``pytest_runtestloop`` wrapper, which only
# runs once every ``pytest_collection`` hook (including the plugin's own
# correction, applied via a hook wrapper around ``pytest_collection``) has
# fully unwound. This is the value that pytest's terminal reporter actually
# uses to compute progress percentages.
_OBSERVER_CONFTEST = """
    import pytest

    @pytest.hookimpl(wrapper=True)
    def pytest_runtestloop(session):
        print("OBSERVED_TESTSCOLLECTED", session.testscollected)
        return (yield)
"""


def test_progress_count_includes_bound_cocotb_tests(pytester: Pytester) -> None:
    """``session.testscollected`` must count cocotb tests bound to a runner.

    Regression test for `#5303
    <https://github.com/cocotb/cocotb/issues/5303>`__: the pytest plugin
    deliberately skips collecting ``@pytest.mark.cocotb_test`` items as their
    own pytest items when they are bound to a ``@pytest.mark.cocotb_runner``
    (they are instead reported over IPC by the runner's simulator subprocess).
    Without correction, pytest's own ``session.testscollected`` therefore only
    counts the runner, so the built-in terminal progress bar exceeds 100% once
    the individual cocotb test reports start arriving.
    """
    pytester.makepyfile(test_testbench=_TESTBENCH_SOURCE)
    pytester.makeconftest(_OBSERVER_CONFTEST)

    result = pytester.runpytest("-p", PLUGIN, "--strict-markers", "-s")

    result.assert_outcomes(passed=1)  # only the runner is a real pytest item
    # 1 runner + 3 cocotb tests bound to it.
    result.stdout.fnmatch_lines(["OBSERVED_TESTSCOLLECTED 4"])


def test_progress_count_matches_plain_collection(pytester: Pytester) -> None:
    """A module with no cocotb markers is unaffected by the plugin's correction."""
    pytester.makepyfile(
        test_plain="""
        def test_a():
            pass

        def test_b():
            pass
        """
    )
    pytester.makeconftest(_OBSERVER_CONFTEST)

    result = pytester.runpytest("-p", PLUGIN, "--strict-markers", "-s")

    result.assert_outcomes(passed=2)
    result.stdout.fnmatch_lines(["OBSERVED_TESTSCOLLECTED 2"])
