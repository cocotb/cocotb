# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test the :mod:`cocotb_tools.pytest._collector` module."""

from __future__ import annotations

import pytest
from pytest import Pytester, RunResult


@pytest.mark.simulator_required
def test_collector_append_dut_test_modules(pytester: Pytester) -> None:
    """Collector should append the :attr:`cocotb_tools.pytest.dut.Dut.test_modules`."""
    test_cocotb: str = """
        import cocotb

        @cocotb.test
        async def test_dut_feature_1(dut) -> None:
            pass
    """

    pytester.makepyfile(
        test_cocotb_1=test_cocotb,
        test_cocotb_2=test_cocotb,
    )

    result: RunResult = pytester.runpytest(
        "--cocotb-regression-manager=cocotb",
    )
    result.assert_outcomes(passed=3)


@pytest.mark.simulator_required
def test_collector_dut_return_annotation(pytester: Pytester) -> None:
    """Test dut fixture the return annotation."""
    pytester.makepyfile(
        test_cocotb="""
        from __future__ import annotations

        import sys
        from typing import Union

        import cocotb
        import pytest

        from cocotb.handle import SimHandleBase
        from cocotb_tools.pytest.dut import Dut

        class MyDut(Dut):
            pass

        @pytest.fixture
        def dut_without_return_annotation(dut):
            return dut

        async def test_1(dut_without_return_annotation):
            pass

        @pytest.fixture
        def dut_with_return_annotation(dut) -> Dut:
            return dut

        async def test_2(dut_without_return_annotation):
            pass

        @pytest.fixture
        def dut_with_union_return_annotation(dut) -> Union[Dut, SimHandleBase]:
            return dut

        async def test_3(dut_with_union_return_annotation):
            pass

        if sys.version_info >= (3, 10):
            @pytest.fixture
            def dut_with_or_return_annotation(dut) -> Dut | SimHandleBase:
                return dut

        async def test_4(dut_with_or_return_annotation):
            pass

        @pytest.fixture
        def dut_with_custom_return_annotation(dut) -> MyDut:
            return dut

        async def test_5(dut_with_custom_return_annotation):
            pass

        @cocotb.test
        async def test_dut(dut):
            pass
        """,
    )

    result: RunResult = pytester.runpytest(
        "--cocotb-regression-manager=cocotb",
    )
    # simulation with 1 cocotb test
    result.assert_outcomes(passed=2)
