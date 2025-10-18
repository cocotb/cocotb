# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Configuration for all tests."""

import os
from pathlib import Path
from shutil import which
from typing import Callable, Optional

from pytest import Parser, PytestPluginManager, TempPathFactory, fixture, hookimpl

from cocotb_tools.runner import Runner, get_runner

PLUGIN: str = "cocotb_tools.pytest.plugin"
DESIGNS: Path = Path(__file__).parent.parent.resolve() / "designs"

# List of VHDL source files
VHDL: list[Path] = [
    DESIGNS / "sample_module" / "sample_module_package.vhdl",
    DESIGNS / "sample_module" / "sample_module_1.vhdl",
    DESIGNS / "sample_module" / "sample_module.vhdl",
]

# List of Verilog/SystemVerilog source files
VERILOG: list[Path] = [
    DESIGNS / "sample_module" / "sample_module.sv",
]

# Name of HDL simulator per executable
SIMULATORS: dict[str, str] = {
    "nvc": "nvc",
    "vcs": "vcs",
    "ghdl": "ghdl",
    "vsim": "questa",
    "xrun": "xcelium",
    "vsimsa": "riviera",
    "iverilog": "icarus",
    "verilator": "verilator",
}

# Supported HDL language per HDL simulator
HDL_TOPLEVEL_LANG: dict[str, str] = {
    "nvc": "vhdl",
    "ghdl": "vhdl",
    "icarus": "verilog",
    "verilator": "verilog",
}

# List of compilation arguments for HDL compiler per HDL simulator
HDL_COMPILE_ARGS: dict[str, list[str]] = {
    "questa": ["+acc"],
    "xcelium": ["-v93"],
    "nvc": ["--std=08"],
    "ghdl": ["-fsynopsys"],
}

# List of simulation arguments per HDL simulator
HDL_SIM_ARGS: dict[str, list[str]] = {
    "questa": ["-t", "ps"],
}


@hookimpl(tryfirst=True)
def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
    """Load pytest cocotb plugin in early stage of pytest when adding options to pytest.

    Args:
        parser: Instance of command line arguments parser used by pytest.
        pluginmanager: Instance of pytest plugin manager.
    """
    if not pluginmanager.has_plugin(PLUGIN):
        pluginmanager.import_plugin(PLUGIN)  # import and register plugin


@fixture(name="hdl_simulator", scope="session")
def hdl_simulator_fixture() -> str:
    """Get name of HDL simulator.

    Based on defined ``SIM`` environment variable or automatically detected based on available command line interface
    (CLI), useful when running tests from container environment which pre-installed HDL simulator.

    Returns:
        Name of detected HDL simulator.
    """
    simulator: str = os.environ.get("SIM", "")

    if not simulator:
        # Automatically detect HDL simulator
        for command, name in SIMULATORS.items():
            if which(command):
                simulator = name
                break

    assert simulator, "No HDL simulator is available to run cocotb"
    return simulator.strip().lower()


@fixture(name="hdl_toplevel_lang", scope="session")
def hdl_toplevel_lang_fixture(hdl_simulator: str) -> str:
    """Get name of HDL language for HDL top level.

    Based on defined ``HDL_TOPLEVEL_LANG`` environment variable when detected HDL simulator supports multiple HDL
    languages or enforced to specific HDL language if not.

    Args:
        hdl_simulator: Name of detected HDL simulator.

    Returns:
        ``vhdl`` or ``verilog``.
    """
    return (
        HDL_TOPLEVEL_LANG.get(
            hdl_simulator, os.environ.get("HDL_TOPLEVEL_LANG", "verilog")
        )
        .strip()
        .lower()
    )


@fixture(name="hdl_sources", scope="session")
def hdl_sources_fixture(hdl_toplevel_lang: str) -> list[Path]:
    """Get list of HDL source files.

    Args:
        hdl_toplevel_lang: Detected HDL language for HDL top level.

    Returns:
        List of HDL source files.
    """
    return VERILOG if hdl_toplevel_lang == "verilog" else VHDL


@fixture(name="hdl_toplevel", scope="session")
def hdl_toplevel_fixture(hdl_sources: list[Path]) -> str:
    """Get name of HDL top level design.

    Args:
        hdl_sources: List of HDL source files.

    Returns:
        Name of HDL top level design.
    """
    return hdl_sources[-1].name.partition(".")[0]


@fixture(name="hdl_timescale", scope="session")
def hdl_timescale_fixture(hdl_simulator: str) -> Optional[tuple[str, str]]:
    """Get timescale for HDL simulator.

    Args:
        hdl_simulator: Name of detected HDL simulator.

    Returns:
        Tuple with time precision and timescale. ``None`` if not supported by HDL simulator.
    """
    return ("1ps", "1ps") if hdl_simulator not in ("xcelium",) else None


@fixture(name="gpi_interfaces", scope="session")
def gpi_interfaces_fixture(hdl_toplevel_lang: str) -> list[str]:
    """Get list of GPI interfaces.

    Args:
        hdl_toplevel_lang: Detected HDL language for HDL top level.

    Returns:
        List of GPI interfaces.
    """
    if hdl_toplevel_lang == "verilog":
        return ["vpi"]

    vhdl_gpi_interface: str | None = os.environ.get("VHDL_GPI_INTERFACE")

    return [vhdl_gpi_interface] if vhdl_gpi_interface else []


@fixture(name="cocotb_runner", scope="session")
def cocotb_runner_fixture(hdl_simulator: str) -> Runner:
    """Get cocotb runner based on name of HDL simulator.

    Args:
        hdl_simulator: Name of HDL simulator.

    Returns:
        Instance of cocotb runner (HDL simulator).
    """
    return get_runner(hdl_simulator)


@fixture(name="hdl_compile_args", scope="session")
def hdl_compile_args_fixture(hdl_simulator: str) -> list[str]:
    """Get list of arguments for HDL compiler.

    Args:
        hdl_simulator: Name of HDL simulator.

    Returns:
        List of arguments for HDL compiler.
    """
    return HDL_COMPILE_ARGS.get(hdl_simulator, [])


@fixture(name="hdl_sim_args", scope="session")
def hdl_sim_args_fixture(hdl_simulator: str) -> list[str]:
    """Get list of arguments for HDL simulator.

    Args:
        hdl_simulator: Name of HDL simulator.

    Returns:
        List of arguments for HDL simulator.
    """
    return HDL_SIM_ARGS.get(hdl_simulator, [])


@fixture(name="cocotb_build", scope="session")
def cocotb_build_fixture(
    cocotb_runner: Runner,
    tmp_path_factory: TempPathFactory,
    hdl_sources: list[Path],
    hdl_toplevel: str,
    hdl_timescale: Optional[tuple[str, str]],
    hdl_compile_args: list[str],
) -> Runner:
    """Compile HDL using cocotb runner (HDL simulator)."""
    cocotb_runner.build(
        sources=hdl_sources,
        hdl_toplevel=hdl_toplevel,
        build_dir=tmp_path_factory.mktemp("build"),
        build_args=hdl_compile_args,
        timescale=hdl_timescale,
    )

    return cocotb_runner


@fixture(name="cocotb_run", scope="session")
def cocotb_run_fixture(
    cocotb_build: Runner,
    hdl_toplevel_lang: str,
    hdl_toplevel: str,
    hdl_sim_args: list[str],
    hdl_timescale: Optional[tuple[str, str]],
    gpi_interfaces: list[str],
) -> Callable[..., None]:
    """Run cocotb using cocotb runner (HDL simulator)."""

    def run(*args, **kwargs) -> None:
        kwargs.setdefault("hdl_toplevel_lang", hdl_toplevel_lang)
        kwargs.setdefault("hdl_toplevel", hdl_toplevel)
        kwargs.setdefault("test_module", f"test_{hdl_toplevel}")
        kwargs.setdefault("test_args", hdl_sim_args)
        kwargs.setdefault("timescale", hdl_timescale)
        kwargs.setdefault("gpi_interfaces", gpi_interfaces)
        cocotb_build.test(*args, **kwargs)

    return run
