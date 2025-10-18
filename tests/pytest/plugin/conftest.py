# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Configuration for all tests."""

from pathlib import Path
from shutil import which
from typing import Callable

from pytest import TempPathFactory, fixture

from cocotb_tools.runner import Ghdl, Runner, get_runner

pytest_plugins = ("cocotb_tools.pytest.plugin",)
DESIGNS: Path = Path(__file__).parent.parent.parent.resolve() / "designs"
TIMESCALE: tuple[str, str] = ("1ps", "1ps")
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
SOURCES: tuple[Path, ...] = (
    DESIGNS / "sample_module" / "sample_module_package.vhdl",
    DESIGNS / "sample_module" / "sample_module_1.vhdl",
    DESIGNS / "sample_module" / "sample_module.vhdl",
)


@fixture(name="cocotb_runner", scope="session")
def cocotb_runner_fixture() -> Runner:
    """Automatically detect HDL simulator."""
    for command, simulator in SIMULATORS.items():
        if which(command):
            return get_runner(simulator)

    return get_runner("")


@fixture(name="cocotb_build", scope="session")
def cocotb_build_fixture(
    cocotb_runner: Runner, tmp_path_factory: TempPathFactory
) -> Runner:
    build_args: list[str] = []

    if isinstance(cocotb_runner, Ghdl):
        build_args.extend(("-fsynopsys",))

    cocotb_runner.build(
        sources=SOURCES,
        hdl_toplevel=SOURCES[-1].name.partition(".")[0],
        build_dir=tmp_path_factory.mktemp("build"),
        build_args=build_args,
        timescale=TIMESCALE,
    )

    return cocotb_runner


@fixture(name="cocotb_run", scope="session")
def cocotb_run_fixture(cocotb_build: Runner) -> Callable[..., None]:
    def run(*args, **kwargs) -> None:
        kwargs.setdefault("timescale", TIMESCALE)
        kwargs.setdefault("hdl_toplevel_lang", "vhdl")
        kwargs.setdefault("hdl_toplevel", "sample_module")
        kwargs.setdefault("test_module", "test_sample_module")
        kwargs.setdefault("gpi_interfaces", [])
        cocotb_build.test(*args, **kwargs)

    return run
