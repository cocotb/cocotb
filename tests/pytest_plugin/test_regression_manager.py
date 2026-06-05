# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test plugin when ``--cocotb-regression-manager=<pytest|cocotb>``."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest import Pytester, RunResult


@pytest.mark.simulator_required
@pytest.mark.parametrize("collect_only", (True, False))
@pytest.mark.parametrize("with_user_runners", (False, True))
@pytest.mark.parametrize("regression_manager", ("pytest", "cocotb"))
def test_regression_manager_with_basic_module(
    pytester: Pytester,
    regression_manager: str,
    with_user_runners: bool,
    collect_only: bool,
) -> None:
    """Test ``pytest --cocotb-regression-manager=<pytest|cocotb> [--cocotb-with-user-runners] [--collect-only]``."""
    tests: int = 32
    passed: int = 26
    skipped: int = 2
    xfailed: int = 0
    xpassed: int = 0

    if regression_manager == "pytest":
        tests += 8
        passed += 4
        xfailed += 7
        xpassed += 1

    elif regression_manager == "cocotb":
        passed += 4

    args: list[str] = [
        f"--cocotb-regression-manager={regression_manager}",
        "--override-ini=markers=order",
    ]

    if with_user_runners:
        args.append("--cocotb-with-user-runners")

    if collect_only:
        args.append("--collect-only")

    pytester.makepyfile(
        test_cocotb='''
        """Cocotb tests."""

        from random import randrange

        import cocotb
        from cocotb.clock import Clock
        from cocotb.triggers import RisingEdge, FallingEdge, SimTimeoutError

        async def simple_transfer(dut) -> None:
            Clock(dut.i_clk, 2, "step").start()

            dut.i_clk.value = 0
            dut.i_rst.value = 1
            dut.i_data.value = 0
            await RisingEdge(dut.i_clk)

            dut.i_rst.value = 0
            await RisingEdge(dut.i_clk)

            value: int = randrange(0, 1 << int(dut.WIDTH.value))

            dut.i_data.value = value
            await RisingEdge(dut.i_clk)

            await FallingEdge(dut.i_clk)
            assert dut.o_data.value == value

            await RisingEdge(dut.i_clk)

        @cocotb.test
        async def test_with_underscore(_) -> None:
            await simple_transfer(_)

        @cocotb.test
        async def test_simple_transfer(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test
        async def without_test_prefix(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test()
        async def test_with_parenthesis(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test(skip=True)
        async def test_skip_true(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test(skip=False)
        async def test_skip_false(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test(stage=0)
        async def test_stage_0(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test(stage=10)
        async def test_stage_10(dut) -> None:
            await simple_transfer(dut)

        @cocotb.parametrize()
        async def test_parametrize_empty(dut) -> None:
            await simple_transfer(dut)

        @cocotb.parametrize(value=(1, 2, 3))
        async def test_parametrize_kwargs(dut, value: int) -> None:
            await simple_transfer(dut)
            assert value in (1, 2, 3)

        @cocotb.parametrize(("value", (1, 2, 3)))
        async def test_parametrize_tuple(dut, value: int) -> None:
            await simple_transfer(dut)
            assert value in (1, 2, 3)

        @cocotb.parametrize(
            ("arg1", [0, 1]),
            (("arg2", "arg3"), [(1, 2), (3, 4)]),
        )
        async def test_parametrize_complex(dut, arg1: int, arg2: int, arg3: int) -> None:
            await simple_transfer(dut)
            assert arg1 in (0, 1)
            assert arg2 in (1, 3)
            assert arg3 in (2, 4)

        @cocotb.test(timeout_time=100, timeout_unit="step")
        async def test_with_timeout_passed(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test(timeout_time=1, timeout_unit="step", expect_fail=True, expect_error=SimTimeoutError)
        async def test_with_timeout_failed(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test(expect_fail=True)
        async def test_expect_fail_true(dut) -> None:
            await simple_transfer(dut)
            assert False

        @cocotb.test(expect_fail=False)
        async def test_expect_fail_false(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test(expect_error=ValueError)
        async def test_expect_error(dut) -> None:
            await simple_transfer(dut)
            raise ValueError("error")

        @cocotb.test(name="test_with_different_name")
        async def test_with_custom_name(dut) -> None:
            await simple_transfer(dut)

        @cocotb.skipif(True, reason="skip test")
        async def test_skipif_true(dut) -> None:
            await simple_transfer(dut)

        @cocotb.skipif(False, reason="don't skip test")
        async def test_skipif_false(dut) -> None:
            await simple_transfer(dut)

        @cocotb.xfail(True, reason="allow test to fail", raises=RuntimeError)
        async def test_xail_true(dut) -> None:
            await simple_transfer(dut)
            raise RuntimeError("error")

        @cocotb.xfail(False, reason="don't allow test to fail")
        async def test_xfail_false(dut) -> None:
            await simple_transfer(dut)

        @cocotb.test
        async def test_with_docstring(dut) -> None:
            """Test DUT feature."""
            await simple_transfer(dut)

        @cocotb.xfail(False, reason="cannot fail")
        @cocotb.xfail(True, reason="can fail")
        async def test_double_xfail(dut) -> None:
            await simple_transfer(dut)
            assert 1 == 2
        '''
    )

    if regression_manager == "pytest":
        pytester.makepyfile(
            test_pytest='''
            """Cocotb tests with pytest."""

            from random import randrange
            from collections.abc import AsyncGenerator

            import pytest
            from pytest import fixture
            from cocotb.clock import Clock
            from cocotb.triggers import RisingEdge, FallingEdge
            from cocotb_tools.pytest.dut import Dut

            @fixture(autouse=True)
            async def clock_generation(dut) -> AsyncGenerator[None, None, None]:
                Clock(dut.i_clk, 2, "step").start()
                yield

                # Workaround for Icarus simulator
                # https://github.com/cocotb/cocotb/issues/5094
                await RisingEdge(dut.i_clk)

            @fixture(autouse=True)
            async def reset_generation(dut) -> None:
                dut.i_clk.value = 0
                dut.i_rst.value = 1
                dut.i_data.value = 0
                await RisingEdge(dut.i_clk)

                dut.i_rst.value = 0
                await RisingEdge(dut.i_clk)

            async def simple_transfer(dut) -> None:
                value: int = randrange(0, 1 << int(dut.WIDTH.value))

                dut.i_data.value = value
                await RisingEdge(dut.i_clk)

                await FallingEdge(dut.i_clk)
                assert dut.o_data.value == value

                # Workaround for Icarus simulator
                # https://github.com/cocotb/cocotb/issues/5094
                await RisingEdge(dut.i_clk)

            @fixture(name="async_generator")
            async def async_generator_fixture(dut) -> AsyncGenerator[Dut, None]:
                # Setup
                await simple_transfer(dut)

                # Call
                yield dut

                # Teardown
                await simple_transfer(dut)

            @fixture(name="value_async_generator")
            async def value_async_generator_fixture(dut) -> AsyncGenerator[int, None]:
                # Setup
                await simple_transfer(dut)

                # Call
                yield 1234

                # Teardown
                await simple_transfer(dut)

            @fixture(name="failed_setup_async_generator")
            async def failed_setup_async_generator_fixture(dut) -> AsyncGenerator[int, None]:
                # Setup
                await simple_transfer(dut)

                raise RuntimeError("error in setup")

                # Call
                yield 1234

                # Teardown
                await simple_transfer(dut)

            @fixture(name="failed_teardown_async_generator")
            async def failed_teardown_async_generator_fixture(dut) -> AsyncGenerator[int, None]:
                # Setup
                await simple_transfer(dut)

                # Call
                yield 1234

                raise RuntimeError("error in teardown")

                # Teardown
                await simple_transfer(dut)

            @fixture(name="coroutine")
            async def coroutine_fixture(dut) -> Dut:
                await simple_transfer(dut)

                return dut

            @fixture(name="value_coroutine")
            async def value_coroutine_fixture(dut) -> int:
                await simple_transfer(dut)

                return 1234

            @fixture(name="failed_coroutine")
            async def failed_coroutine_fixture(dut) -> int:
                await simple_transfer(dut)

                raise RuntimeError("error in coroutine")

                return 1234

            async def test_simple_transfer(dut) -> None:
                await simple_transfer(dut)

            async def test_with_async_generator_fixture(async_generator) -> None:
                await simple_transfer(async_generator)

            async def test_with_coroutine_fixture(coroutine) -> None:
                await simple_transfer(coroutine)

            async def test_value_from_async_generator_fixture(value_async_generator: int) -> None:
                assert value_async_generator == 1234

            async def test_value_from_coroutine_fixture(value_coroutine: int) -> None:
                assert value_coroutine == 1234

            @pytest.mark.xfail(raises=RuntimeError)
            async def test_with_failed_setup_async_generator_fixture(failed_setup_async_generator: int) -> None:
                assert failed_setup_async_generator == 1234

            @pytest.mark.xfail(raises=RuntimeError)
            async def test_with_failed_teardown_async_generator_fixture(failed_teardown_async_generator: int) -> None:
                assert failed_teardown_async_generator == 1234

            @pytest.mark.xfail(raises=RuntimeError)
            async def test_with_failed_coroutine_fixture(failed_coroutine: int) -> None:
                assert failed_coroutine == 1234
            '''
        )

    if with_user_runners:
        pytester.makepyfile(
            test_runner='''
            """Cocotb runner."""
            from pathlib import Path
            from argparse import Namespace

            from pytest import FixtureRequest
            from cocotb_tools.runner import Runner, get_runner

            DIR = Path(__file__).parent.resolve()

            def test_runner(request: FixtureRequest) -> None:
                option: Namespace = request.config.option

                test_modules: list[str] = ["test_cocotb"]

                if option.cocotb_regression_manager == "pytest":
                    test_modules += ["test_pytest"]

                sources: list[Path] = []

                if option.cocotb_toplevel_lang == "verilog":
                    sources = [DIR / "top.sv"]

                elif option.cocotb_toplevel_lang == "vhdl":
                    sources = [DIR / "top.vhd"]

                runner: Runner = get_runner(option.cocotb_simulator)

                runner.build(
                    sources=sources,
                    hdl_toplevel="top",
                )

                runner.test(
                    test_module=test_modules,
                    hdl_toplevel="top",
                    gpi_interfaces=option.cocotb_gpi_interfaces or None,
                )
            '''
        )

        pytester.makeconftest(
            '''
            """DUT fixture."""
            from pytest import fixture
            from cocotb_tools.pytest.dut import Dut

            @fixture(name="_")
            def underscore_fixture(dut: Dut) -> Dut:
                return dut
            '''
        )

    else:
        pytester.makeconftest(
            '''
            """DUT fixture."""
            from pathlib import Path

            from pytest import FixtureRequest, fixture
            from cocotb_tools.pytest.dut import Dut

            DIR = Path(__file__).parent.resolve()

            @fixture(name="dut")
            def dut_fixture(dut: Dut, request: FixtureRequest) -> Dut:
                dut.test_modules = ["test_cocotb"]

                if request.config.option.cocotb_regression_manager == "pytest":
                    dut.test_modules += ["test_pytest"]

                if dut.toplevel_lang == "verilog":
                    dut.sources = [DIR / "top.sv"]

                elif dut.toplevel_lang == "vhdl":
                    dut.sources = [DIR / "top.vhd"]

                return dut

            @fixture(name="_")
            def underscore_fixture(dut: Dut) -> Dut:
                return dut
            '''
        )

    result: RunResult = pytester.runpytest(*args)
    assert not result.ret

    if collect_only:
        assert result.parseoutcomes()["tests"] == tests
    else:
        result.assert_outcomes(
            passed=passed, skipped=skipped, xfailed=xfailed, xpassed=xpassed
        )


@pytest.mark.simulator_required
@pytest.mark.parametrize("collect_only", (True, False))
@pytest.mark.parametrize("with_user_runners", (False, True))
@pytest.mark.parametrize("regression_manager", ("pytest", "cocotb"))
def test_regression_manager_with_sample_module(
    pytester: Pytester,
    regression_manager: str,
    with_user_runners: bool,
    collect_only: bool,
    designs_dir: Path,
    test_cocotb_dir: Path,
) -> None:
    """Test ``pytest --cocotb-regression-manager=<pytest|cocotb> [--cocotb-with-user-runners] [--collect-only]``."""
    args: list[str] = [
        f"--cocotb-regression-manager={regression_manager}",
        "--override-ini=markers=order",
        f"--override-ini=pythonpath={test_cocotb_dir.as_posix()}",
    ]

    excludes: list[str] = []

    if with_user_runners:
        args.append("--cocotb-with-user-runners")

    if collect_only:
        args.append("--collect-only")

    if regression_manager == "pytest":
        excludes += [
            # Pytest is capturing logs, this test will always fail
            "test_logging.test_logging_with_args",
            # TestSuccess is not a valid concept in pytest, user must use the @pytest.mark.xfail() marker
            "test_deprecated.test_pass_test_in_",
            # Pytest is naming parametrized tests different than cocotb built-in regression manager
            "test_testfactory.test_testfactory_verify_names",
            "test_testfactory.test_params_verify_names",
            # Old way of handling cocotb tests
            "test_deprecated.test_testfactory_deprecated",
            # We are working directly in pytest
            "pytest_assertion_rewriting.test_assertion_rewriting",
            # Broken for TestManager.__repr__
            "test_scheduler.test_test_repr",
        ]

    if excludes:
        args.extend(("-k", "not " + " and not ".join(excludes)))

    if with_user_runners:
        pytester.makeconftest("""
            import pytest
            from cocotb_tools.pytest.dut import Dut

            @pytest.fixture(name="_")
            def underscore_fixture(dut: Dut) -> Dut:
                return dut
        """)

        pytester.makepyfile(
            test_runner=f'''
            """Cocotb runner."""
            from pathlib import Path
            from argparse import Namespace

            from pytest import FixtureRequest
            from cocotb_tools.runner import Runner, get_runner

            DESIGNS_DIR: Path = Path(r"{designs_dir.as_posix()}")

            def test_runner(request: FixtureRequest) -> None:
                option: Namespace = request.config.option

                sources: list[Path] = []

                if option.cocotb_toplevel_lang == "vhdl":
                    sources += [
                        DESIGNS_DIR / "sample_module" / "sample_module_package.vhdl",
                        DESIGNS_DIR / "sample_module" / "sample_module_1.vhdl",
                        DESIGNS_DIR / "sample_module" / "sample_module.vhdl",
                    ]
                elif option.cocotb_toplevel_lang == "verilog":
                    sources += [
                        DESIGNS_DIR / "sample_module" / "sample_module.sv",
                    ]

                test_modules: list[str] = [
                    "test_async_coroutines",
                    "test_async_generators",
                    "test_clock",
                    "test_first_combine",
                    "test_deprecated",
                    "test_edge_triggers",
                    "test_handle",
                    "test_logging",
                    "pytest_assertion_rewriting",
                    "test_queues",
                    "test_scheduler",
                    "test_synchronization_primitives",
                    "test_testfactory",
                    "test_tests",
                    "test_timing_triggers",
                    "test_sim_time_utils",
                ]

                build_args: list[str] = []
                sim_args: list[str] = []
                timescale: tuple[str, str] | None = None

                if option.cocotb_simulator == "questa":
                    build_args += ["+acc"]
                    sim_args += ["-t", "ps"]

                elif option.cocotb_simulator == "xcelium":
                    build_args += ["-v93"]

                elif option.cocotb_simulator == "nvc":
                    build_args += ["--std=08"]

                if option.cocotb_simulator not in ("xcelium",):
                    # test_timing_triggers.py requires a 1ps time precision.
                    timescale = ("1ps", "1ps")

                runner: Runner = get_runner(option.cocotb_simulator)

                runner.build(
                    sources=sources,
                    hdl_toplevel="sample_module",
                    build_args=build_args,
                )

                runner.test(
                    test_module=test_modules,
                    hdl_toplevel="sample_module",
                    test_args=sim_args,
                    timescale=timescale,
                    gpi_interfaces=option.cocotb_gpi_interfaces or None,
                )
            '''
        )

    else:
        pytester.makeconftest(
            f'''
            """DUT fixture."""
            import pytest
            from pathlib import Path
            from cocotb_tools.pytest.dut import Dut

            DESIGNS_DIR: Path = Path(r"{designs_dir.as_posix()}")

            @pytest.fixture(name="dut")
            def dut_fixture(dut: Dut) -> Dut:
                if dut.toplevel_lang == "vhdl":
                    dut.sources += [
                        DESIGNS_DIR / "sample_module" / "sample_module_package.vhdl",
                        DESIGNS_DIR / "sample_module" / "sample_module_1.vhdl",
                        DESIGNS_DIR / "sample_module" / "sample_module.vhdl",
                    ]
                elif dut.toplevel_lang == "verilog":
                    dut.sources += [
                        DESIGNS_DIR / "sample_module" / "sample_module.sv",
                    ]

                dut.test_modules = [
                    "test_async_coroutines",
                    "test_async_generators",
                    "test_clock",
                    "test_first_combine",
                    "test_deprecated",
                    "test_edge_triggers",
                    "test_handle",
                    "test_logging",
                    "pytest_assertion_rewriting",
                    "test_queues",
                    "test_scheduler",
                    "test_synchronization_primitives",
                    "test_testfactory",
                    "test_tests",
                    "test_timing_triggers",
                    "test_sim_time_utils",
                ]

                if dut.simulator == "questa":
                    dut.build_args += ["+acc"]
                    dut.sim_args += ["-t", "ps"]

                elif dut.simulator == "xcelium":
                    dut.build_args += ["-v93"]

                elif dut.simulator == "nvc":
                    dut.build_args += ["--std=08"]

                if dut.simulator not in ("xcelium",):
                    # test_timing_triggers.py requires a 1ps time precision.
                    dut.timescale = ("1ps", "1ps")

                return dut

            @pytest.fixture(name="_")
            def underscore_fixture(dut: Dut) -> Dut:
                return dut
            '''
        )

        pytester.makepyfile(
            """
            import cocotb

            @cocotb.test
            async def test_enforce_creation_of_dut_fixture(dut) -> None:
                pass
            """
        )

    result: RunResult = pytester.runpytest(*args)
    assert not result.ret
