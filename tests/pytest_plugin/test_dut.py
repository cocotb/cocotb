# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test :class:`cocotb_tools.pytest.dut.Dut` class and :func:`cocotb_tools.pytest.plugin.dut` fixture."""

from __future__ import annotations

import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from pytest import MonkeyPatch, Pytester, RunResult, fixture

#: List of possible option values used during plugin testing
OPTION_VALUE: tuple[tuple[str, object], ...] = (
    ("cocotb_library", "worklib"),
    ("cocotb_simulator", "verilator"),
    ("cocotb_toplevel_lang", "verilog"),
    ("cocotb_toplevel_lang", "vhdl"),
    ("cocotb_toplevel_library", "toplib"),
    ("cocotb_gui", False),
    ("cocotb_gui", True),
    ("cocotb_waves", False),
    ("cocotb_waves", True),
    ("cocotb_clean", False),
    ("cocotb_clean", True),
    ("cocotb_always", False),
    ("cocotb_always", True),
    ("cocotb_verbose", False),
    ("cocotb_verbose", True),
    ("cocotb_build_dir", "build"),
    ("cocotb_random_seed", 0),
    ("cocotb_random_seed", 1234),
    ("cocotb_sources", []),
    ("cocotb_sources", ["src1.sv"]),
    ("cocotb_sources", ["src1.vhd", "src2.vhd"]),
    ("cocotb_defines", {}),
    ("cocotb_defines", {"define1": "value1"}),
    ("cocotb_defines", {"define1": "value1", "define2": "value2"}),
    ("cocotb_includes", []),
    ("cocotb_includes", ["incdir1"]),
    ("cocotb_includes", ["incdir1", "incdir2"]),
    ("cocotb_parameters", {}),
    ("cocotb_parameters", {"param1": "value1"}),
    ("cocotb_parameters", {"param1": "value1", "param2": "value2"}),
    ("cocotb_timescale", "1ns / 1ps"),
    ("cocotb_build_args", []),
    ("cocotb_build_args", ["-sv"]),
    ("cocotb_build_args", ["-sv", "-uvm", "-tcl", "set x 2"]),
    ("cocotb_elab_args", []),
    ("cocotb_elab_args", ["-incr"]),
    ("cocotb_elab_args", ["-incr", "-stats", "-coverage", "module expr"]),
    ("cocotb_sim_args", []),
    ("cocotb_sim_args", ["-snapshot"]),
    ("cocotb_sim_args", ["-snapshot", "-tcl", "set ignore_warnings 1"]),
    ("cocotb_env", {}),
    ("cocotb_env", {"VAR1": "value1"}),
    ("cocotb_env", {"VAR1": "value1", "VAR2": "value2"}),
    ("cocotb_plusargs", []),
    ("cocotb_plusargs", ["+ARG1"]),
    ("cocotb_plusargs", ["+ARG1=value1", "+ARG2=value2"]),
    ("cocotb_gpi_interfaces", []),
    ("cocotb_gpi_interfaces", ["vhdl"]),
    ("cocotb_gpi_interfaces", ["verilog"]),
    ("cocotb_gpi_interfaces", ["verilog", "vhdl"]),
    ("cocotb_pre_cmd", []),
    ("cocotb_pre_cmd", ["cmd"]),
    ("cocotb_pre_cmd", ["cmd", "arg1", "arg2 arg3"]),
    ("cocotb_test_filter", "^test_.*$"),
)


@fixture(name="pytester")
def pytester_fixture(pytester: Pytester) -> Pytester:
    """Setup :class:`pytest.Pytester` fixture."""
    pytester.makeconftest("")  # Nuke conftest.py

    return pytester


def make_test_file(
    pytester: Pytester,
    option: str,
    value: object,
    marker: str = "",
) -> None:
    """Create ``test_*.py`` file that will be used to test plugin."""
    attr: str = option.split("_", maxsplit=1)[1]

    if option == "cocotb_timescale" and isinstance(value, str):
        value = tuple(map(str.strip, value.split("/", maxsplit=1)))

    # It creates the 'pytest.ini' file
    # https://docs.pytest.org/en/stable/reference/customize.html#pytest-ini
    pytester.makefile(
        ".ini",
        pytest="""
        [pytest]
        addopts = --verbose --capture no --strict-markers -p cocotb_tools.pytest.plugin
        """,
    )

    pytester.makepyfile(f"""
        from pathlib import Path

        import pytest

        from cocotb_tools.pytest.dut import Dut

        def normalize(value):
            if isinstance(value, Path):
                return str(value.name)

            return value

        {marker}
        def test_option(dut: Dut) -> None:
            value = dut.{attr}

            if isinstance(value, list):
                value = list(map(normalize, value))
            else:
                value = normalize(value)

            assert value == {value!r}
    """)


@pytest.mark.parametrize("option,value", OPTION_VALUE)
def test_dut_option_from_environment_variable(
    pytester: Pytester,
    monkeypatch: MonkeyPatch,
    option: str,
    value: object,
) -> None:
    """Test configuring :class:`cocotb_tools.pytest.dut.Dut` fixture from environment variables."""
    make_test_file(pytester, option, value)

    if isinstance(value, Mapping):
        value = ",".join(f"{k}={v}" for k, v in value.items())
    elif isinstance(value, Sequence) and not isinstance(value, str):
        if option.endswith("_args") or option == "cocotb_pre_cmd":
            value = shlex.join(value)
        else:
            value = ",".join(value)
    else:
        value = str(value)

    monkeypatch.setenv(option.upper(), value)
    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("option,value", OPTION_VALUE)
def test_dut_option_from_configuration_file(
    pytester: Pytester,
    monkeypatch: MonkeyPatch,
    option: str,
    value: object,
) -> None:
    """Test configuring :class:`cocotb_tools.pytest.dut.Dut` fixture from pytest configuration file."""
    make_test_file(pytester, option, value)

    if isinstance(value, Mapping):
        value = " ".join(f'"{k}={v}"' for k, v in value.items())
    elif isinstance(value, Sequence) and not isinstance(value, str):
        if option.endswith("_args") or option == "cocotb_pre_cmd":
            value = shlex.join(value)
        else:
            value = " ".join(value)

    # It creates the 'pytest.ini' file
    # https://docs.pytest.org/en/stable/reference/customize.html#pytest-ini
    pytester.makefile(
        ".ini",
        pytest=f"""
        [pytest]
        addopts = --verbose --capture no --strict-markers -p cocotb_tools.pytest.plugin
        {option} = {value}
        """,
    )

    monkeypatch.delenv(option.upper(), raising=False)
    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("option,value", OPTION_VALUE)
def test_dut_option_from_command_line(
    pytester: Pytester,
    monkeypatch: MonkeyPatch,
    option: str,
    value: object,
) -> None:
    """Test configuring :class:`cocotb_tools.pytest.dut.Dut` fixture from pytest command line interface."""
    make_test_file(pytester, option, value)

    args: list[str] = [f"--{option.replace('_', '-')}"]

    if value is False:
        args = []
    elif value is True:
        pass
    elif isinstance(value, Mapping):
        args.extend(f"{k}={v}" for k, v in value.items())
    elif isinstance(value, Sequence) and not isinstance(value, str):
        if option.endswith("_args") or option == "cocotb_pre_cmd":
            args = [args[0] + "=" + shlex.join(value)]
        else:
            args.extend(map(str, value))
    else:
        args.append(str(value))

    monkeypatch.delenv(option.upper(), raising=False)
    result: RunResult = pytester.runpytest(*args)
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("option,value", OPTION_VALUE)
def test_dut_option_from_marker(
    pytester: Pytester,
    monkeypatch: MonkeyPatch,
    option: str,
    value: object,
) -> None:
    """Test configuring :class:`cocotb_tools.pytest.dut.Dut` fixture from pytest ``@pytest.mark.cocotb_*`` markers."""
    marker: str = f"@pytest.mark.{option}"

    if isinstance(value, Sequence) and not isinstance(value, str):
        marker += "(" + ", ".join(f"{arg!r}" for arg in value) + ")"
    elif isinstance(value, Mapping):
        marker += "(" + ", ".join(f"{key}={arg!r}" for key, arg in value.items()) + ")"
    elif value is not True:
        marker += f"({value!r})"

    make_test_file(pytester, option, value, marker=marker)

    monkeypatch.delenv(option.upper(), raising=False)
    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "option,default",
    (
        ("cocotb_library", "top"),
        ("cocotb_toplevel", "dut_option_default"),
        ("cocotb_toplevel_library", "top"),
        ("cocotb_gui", False),
        ("cocotb_waves", False),
        ("cocotb_clean", False),
        ("cocotb_always", False),
        ("cocotb_verbose", False),
        ("cocotb_build_dir", "sim_build"),
        ("cocotb_sources", []),
        ("cocotb_defines", {}),
        ("cocotb_includes", []),
        ("cocotb_parameters", {}),
        ("cocotb_timescale", None),
        ("cocotb_build_args", []),
        ("cocotb_elab_args", []),
        ("cocotb_sim_args", []),
        ("cocotb_env", {}),
        ("cocotb_plusargs", []),
        ("cocotb_gpi_interfaces", []),
        ("cocotb_pre_cmd", []),
        ("cocotb_test_modules", ["test_dut_option_default"]),
        ("cocotb_test_filter", ""),
    ),
)
def test_dut_option_default(
    pytester: Pytester,
    monkeypatch: MonkeyPatch,
    option: str,
    default: object,
) -> None:
    """Test default values of :class:`cocotb_tools.pytest.dut.Dut` fixture."""
    make_test_file(pytester, option, default)

    monkeypatch.delenv(option.upper(), raising=False)
    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


@pytest.mark.simulator_required
def test_dut_run(pytester: Pytester, designs_dir: Path, test_cocotb_dir: Path) -> None:
    """Test invocation of the :meth:`cocotb_tools.pytest.dut.Dut.run` method."""
    pytester.makeconftest(f"""
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
    """)

    pytester.makepyfile("""
        from cocotb_tools.pytest.dut import Dut

        def test_cocotb_runner(dut: Dut) -> None:
            dut.run()
    """)

    result: RunResult = pytester.runpytest(
        "--cocotb-regression-manager=cocotb",
        f"--override-ini=pythonpath={test_cocotb_dir.as_posix()}",
    )
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "marker",
    (
        "xoxotb_",
        "cocotb_",
        "cocotb_unknown",
        "cocotb__private",
    ),
)
def test_dut_marker_invalid(pytester: Pytester, marker: str) -> None:
    """Test invalid markers."""
    pytester.makepyfile(f"""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        @pytest.mark.{marker}
        def test_invalid_marker(dut: Dut) -> None:
            pass
    """)

    result: RunResult = pytester.runpytest(f"--override-ini=markers={marker}")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "marker",
    (
        "cocotb_sources('adder.sv', 'top.v')",
        "cocotb_sources('adder.sv', 'top.sv')",
        "cocotb_sources('adder.sv', 'top.vlt')",
        "cocotb_sources('adder.sv', 'top.vhd')",
        "cocotb_sources('adder.sv', 'top.vhdl')",
        "cocotb_sources('adder.sv', 'top.e.vhd')",
        "cocotb_sources('adder.sv', 'top.e.vhdl')",
        "cocotb_sources('adder.sv', Verilog('top.v'))",
        "cocotb_sources('adder.sv', VHDL('top.vhd'))",
        "cocotb_sources('adder.sv', VerilatorControlFile('top.vlt'))",
    ),
)
def test_dut_toplevel_from_sources(pytester: Pytester, marker: str) -> None:
    """Test toplevel based on source file."""
    pytester.makepyfile(f"""
        import pytest
        from cocotb_tools.pytest.dut import Dut
        from cocotb_tools.runner import Verilog, VHDL, VerilatorControlFile

        @pytest.mark.{marker}
        def test_toplevel(dut: Dut) -> None:
            assert dut.toplevel == "top"
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "marker",
    (
        "cocotb_test_modules('tests.test_top')",
        "cocotb_test_modules('tests.top_test')",
        "cocotb_test_modules('tests.top')",
        "cocotb_test_modules('tests.test_top', 'tests.extra')",
        "cocotb_test_modules('tests.top_test', 'tests.extra')",
        "cocotb_test_modules('tests.top', 'tests.extra')",
    ),
)
def test_dut_toplevel_from_test_modules(pytester: Pytester, marker: str) -> None:
    """Test toplevel based on test module."""
    pytester.makepyfile(f"""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        @pytest.mark.{marker}
        def test_toplevel(dut: Dut) -> None:
            assert dut.toplevel == "top"
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_toplevel_from_attribute(pytester: Pytester) -> None:
    """Test toplevel set from the :attr:`cocotb_tools.pytest.dut.Dut.toplevel` attribute."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            dut.toplevel = "top"
            return dut

        def test_toplevel(dut: Dut) -> None:
            assert dut.toplevel == "top"
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_toplevel_from_marker(pytester: Pytester) -> None:
    """Test toplevel set from the ``@pytest.mark.cocotb_toplevel`` marker."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        @pytest.mark.cocotb_toplevel("top")
        def test_toplevel(dut: Dut) -> None:
            assert dut.toplevel == "top"
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_toplevel_none(pytester: Pytester) -> None:
    """Test toplevel when test modules are empty."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            dut.test_modules = []
            return dut

        def test_toplevel(dut: Dut) -> None:
            assert dut.toplevel == None
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "marker",
    (
        "cocotb_sources('adder.vhd', 'top.v')",
        "cocotb_sources('adder.vhd', 'top.sv')",
        "cocotb_sources('adder.vhd', Verilog('top.v'))",
    ),
)
def test_dut_toplevel_lang_verilog(pytester: Pytester, marker: str) -> None:
    """Test toplevel language based on source file."""
    pytester.makefile(
        ".ini",
        pytest="""
        [pytest]
        addopts = --verbose --capture no --strict-markers -p cocotb_tools.pytest.plugin
        """,
    )

    pytester.makepyfile(f"""
        import pytest
        from cocotb_tools.pytest.dut import Dut
        from cocotb_tools.runner import Verilog, VerilatorControlFile

        @pytest.mark.{marker}
        def test_toplevel(dut: Dut) -> None:
            assert dut.toplevel_lang == "verilog"
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize(
    "marker",
    (
        "cocotb_sources('adder.sv', 'top.vhd')",
        "cocotb_sources('adder.sv', 'top.vhdl')",
        "cocotb_sources('adder.sv', 'top.e.vhd')",
        "cocotb_sources('adder.sv', 'top.e.vhdl')",
        "cocotb_sources('adder.sv', VHDL('top.vhd'))",
    ),
)
def test_dut_toplevel_lang_vhdl(pytester: Pytester, marker: str) -> None:
    """Test toplevel language based on source file."""
    pytester.makefile(
        ".ini",
        pytest="""
        [pytest]
        addopts = --verbose --capture no --strict-markers -p cocotb_tools.pytest.plugin
        """,
    )

    pytester.makepyfile(f"""
        import pytest
        from cocotb_tools.pytest.dut import Dut
        from cocotb_tools.runner import VHDL

        @pytest.mark.{marker}
        def test_toplevel(dut: Dut) -> None:
            assert dut.toplevel_lang == "vhdl"
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_defines_attr_dict(pytester: Pytester) -> None:
    """Test defines."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        DEFINES: dict[str, object] = {
            "DEFINE1": "string",
            "DEFINE2": 1234,
            "DEFINE3": 1.25,
            "DEFINE4": True,
        }

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            dut.defines = DEFINES
            return dut

        def test_toplevel(dut: Dut) -> None:
            assert dut.defines == DEFINES
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_defines_attr_list(pytester: Pytester) -> None:
    """Test defines."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            dut.defines = ["DEFINE1=VALUE1", "DEFINE2=VALUE2"]
            return dut

        def test_toplevel(dut: Dut) -> None:
            assert dut.defines == {
                "DEFINE1": "VALUE1",
                "DEFINE2": "VALUE2",
            }
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_parameters_attr_dict(pytester: Pytester) -> None:
    """Test parameters."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        PARAMS: dict[str, object] = {
            "PARAM1": "string",
            "PARAM2": 1234,
            "PARAM3": 1.25,
            "PARAM4": True,
        }

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            dut.parameters = PARAMS
            return dut

        def test_toplevel(dut: Dut) -> None:
            assert dut.parameters == PARAMS
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_parameters_attr_set(pytester: Pytester) -> None:
    """Test parameters."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        PARAMS: dict[str, object] = {
            "PARAM1": "string",
            "PARAM2": 1234,
            "PARAM3": 1.25,
            "PARAM4": True,
        }

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            for name, value in PARAMS.items():
                dut[name] = value
            return dut

        def test_toplevel(dut: Dut) -> None:
            for name, value in PARAMS.items():
                assert dut[name] == value
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_parameters_attr_list(pytester: Pytester) -> None:
    """Test parameters."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            dut.parameters = ["PARAM1=VALUE1", "PARAM2=VALUE2"]
            return dut

        def test_toplevel(dut: Dut) -> None:
            assert dut.parameters == {
                "PARAM1": "VALUE1",
                "PARAM2": "VALUE2",
            }
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_env_attr_dict(pytester: Pytester) -> None:
    """Test env."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        ENVS: dict[str, object] = {
            "ENV1": "string",
            "ENV2": 1234,
            "ENV3": 1.25,
            "ENV4": True,
        }

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            dut.env = ENVS
            return dut

        def test_toplevel(dut: Dut) -> None:
            assert dut.env == ENVS
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_dut_env_attr_list(pytester: Pytester) -> None:
    """Test env."""
    pytester.makepyfile("""
        import pytest
        from cocotb_tools.pytest.dut import Dut

        @pytest.fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            dut.env = ["ENV1=VALUE1", "ENV2=VALUE2"]
            return dut

        def test_toplevel(dut: Dut) -> None:
            assert dut.env == {
                "ENV1": "VALUE1",
                "ENV2": "VALUE2",
            }
    """)

    result: RunResult = pytester.runpytest()
    result.assert_outcomes(passed=1)
