# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test plugin when ``--cocotb-regression-manager=cocotb``."""

from __future__ import annotations

import pytest
from pytest import Pytester, RunResult, fixture


@fixture(name="pytester")
def pytester_fixture(pytester: Pytester) -> Pytester:
    """Create and add a test file with cocotb tests."""
    pytester.makepyfile(
        test_cocotb_1='''
        """Cocotb tests."""

        import pytest
        import cocotb

        @cocotb.test
        async def test_dut_feature_1(dut) -> None:
            pass

        @cocotb.test
        async def dut_feature_2(dut) -> None:
            pass

        @cocotb.test
        async def dut_feature_3(_) -> None:
            pass

        @cocotb.parametrize(value=(1, 2, 3))
        async def dut_feature_4(dut, value: int) -> None:
            pass

        @cocotb.parametrize(("value", (1, 2, 3)))
        async def dut_feature_5(dut, value: int) -> None:
            pass

        @cocotb.test(timeout_time=10, timeout_unit="step")
        async def dut_feature_6(dut) -> None:
            pass

        @cocotb.test(expect_fail=True)
        async def dut_feature_7(dut) -> None:
            assert False

        @cocotb.test(expect_error=ValueError)
        async def dut_feature_8(dut) -> None:
            raise ValueError("error")

        @cocotb.test(skip=True)
        async def dut_feature_9(dut) -> None:
            pass

        @cocotb.test(stage=10)
        async def dut_feature_10(dut) -> None:
            pass

        @cocotb.test(name="test_dut_feature")
        async def dut_feature_11(dut) -> None:
            pass

        @cocotb.test()
        async def dut_feature_12(dut) -> None:
            pass

        @cocotb.parametrize()
        async def dut_feature_13(dut) -> None:
            pass

        @cocotb.test
        async def dut_feature_14(dut) -> None:
            """Test DUT feature 14."""

        @cocotb.test
        async def dut_feature_15(dut) -> None:
            assert 1 == 2

        @cocotb.test
        async def dut_feature_16(dut) -> None:
            assert 3 == 4, "3 cannot equal 4"

        @cocotb.test
        async def dut_feature_17(dut) -> None:
            raise RuntimeError()

        @cocotb.test
        async def dut_feature_18(dut) -> None:
            raise RuntimeError("error message")

        class MyError(RuntimeError):
            pass

        @cocotb.test
        async def dut_feature_19(dut) -> None:
            raise MyError("error message")

        @cocotb.parametrize(
            ("arg1", [0, 1]),
            (("arg2", "arg3"), [(1, 2), (3, 4)]),
        )
        async def dut_feature_20(dut, arg1: int, arg2: int, arg3: int) -> None:
            assert arg1 in (0, 1)
            assert arg2 in (1, 3)
            assert arg3 in (2, 4)
    '''
    )

    pytester.makepyfile(
        test_cocotb_2='''
        """Cocotb tests."""

        import pytest
        import cocotb

        @cocotb.test
        @pytest.mark.cocotb_parameters(WIDTH=8)
        async def dut_feature_21(dut) -> None:
            pass
        '''
    )

    return pytester


@pytest.mark.simulator_required
@pytest.mark.parametrize("with_user_runners", (False, True))
def test_manager_cocotb_collect(pytester: Pytester, with_user_runners: bool) -> None:
    """Test ``pytest --cocotb-regression-manager=cocotb --collect-only``."""
    tests: int = 30

    args: list[str] = [
        "--cocotb-regression-manager=cocotb",
        "--override-ini=markers=order",
        "--collect-only",
    ]

    if with_user_runners:
        # Test function with the dut.run() will be not created by the plugin
        tests -= 2
        args.append("--cocotb-with-user-runners")

    result: RunResult = pytester.runpytest(*args)
    assert not result.ret
    assert result.parseoutcomes()["tests"] == tests


@pytest.mark.simulator_required
@pytest.mark.parametrize("with_user_runners", (False, True))
def test_manager_cocotb_runner(pytester: Pytester, with_user_runners: bool) -> None:
    """Test ``pytest --cocotb-regression-manager=cocotb``."""
    passed: int = 23
    failed: int = 6
    skipped: int = 1

    args: list[str] = [
        "--cocotb-regression-manager=cocotb",
        "--override-ini=markers=order",
    ]

    if with_user_runners:
        # Test function with the dut.run() will be not created by the plugin
        args.append("--cocotb-with-user-runners")

    if with_user_runners:
        passed -= 1

        pytester.makepyfile(
            test_runner="""
            from cocotb_tools.pytest.dut import Dut
            from cocotb_tools.runner import Runner, get_runner

            def test_runner(dut: Dut) -> None:
                runner: Runner = get_runner(dut.simulator)

                runner.build(
                    sources=dut.sources,
                    hdl_toplevel=dut.toplevel,
                )

                runner.test(
                    test_module=["test_cocotb_1", "test_cocotb_2"],
                    hdl_toplevel=dut.toplevel,
                )
            """
        )

    result: RunResult = pytester.runpytest(*args)
    assert result.ret
    result.assert_outcomes(passed=passed, failed=failed, skipped=skipped)
