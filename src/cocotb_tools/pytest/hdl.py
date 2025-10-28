# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Build and test HDL designs."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from shutil import which

from pytest import Config, FixtureRequest

from cocotb_tools.runner import (
    VHDL,
    PathLike,
    Runner,
    VerilatorControlFile,
    Verilog,
    get_runner,
)

POSIX_PATH: re.Pattern = re.compile(r"[^A-Za-z0-9/._-]")

# Name of HDL simulator per executable
# TODO: Move to cocotb_tools.runner?
SIMULATORS: dict[str, str] = {
    # open-source simulators first
    "verilator": "verilator",
    "nvc": "nvc",
    "ghdl": "ghdl",
    "iverilog": "icarus",
    # proprietary simulators
    "xrun": "xcelium",
    "vcs": "vcs",
    "vsim": "questa",
    "vsimsa": "riviera",
}


def get_simulator(config: Config) -> str:
    """Get name of HDL simulator.

    Args:
        config: Pytest configuration object.

    Returns:
        Name of HDL simulator.
    """
    simulator: str = config.option.cocotb_simulator

    if not simulator or simulator == "auto":
        for command, name in SIMULATORS.items():
            if which(command):
                return name

    return simulator


class HDL:
    """Build HDL design and run test against specific HDL top level."""

    def __init__(self, request: FixtureRequest):
        option = request.config.option
        nodeid: str = request.node.nodeid

        # Use only allowed characters by POSIX standard
        # Pytest is always using "/" as path separator regardless of current OS environment
        nodeid = POSIX_PATH.sub("_", nodeid.replace(".py::", "/").replace("::", "/"))

        if os.path.sep != "/":
            nodeid = nodeid.replace("/", os.path.sep)

        self.test_dir: Path = Path(option.cocotb_build_dir).resolve() / nodeid
        self.runner: Runner = get_runner(get_simulator(request.config))

        # Build options
        self.library: str = option.cocotb_library
        self.sources: Sequence[PathLike | VHDL | Verilog | VerilatorControlFile] = []
        self.includes: Sequence[PathLike] = option.cocotb_includes
        self.defines: Mapping[str, object] = option.cocotb_defines
        self.parameters: Mapping[str, object] = option.cocotb_parameters
        self.build_args: Sequence[str | VHDL | Verilog] = option.cocotb_build_args
        self.toplevel: str | None = option.cocotb_toplevel
        self.always: bool = option.cocotb_always
        self.clean: bool = option.cocotb_clean
        self.verbose: bool = option.cocotb_verbose
        self.timescale: tuple[str, str] | None = option.cocotb_timescale
        self.waves: bool = option.cocotb_waves

        # Test options
        self.test_module: str | Sequence[str] = option.cocotb_test_modules
        self.toplevel_library: str = option.cocotb_toplevel_library
        self.toplevel_lang: str | None = option.cocotb_toplevel_lang
        self.gpi_interfaces: list[str] | None = option.cocotb_gpi_interfaces
        self.testcase: str | Sequence[str] | None = option.cocotb_testcase
        self.seed: str | int | None = option.cocotb_seed
        self.elab_args: Sequence[str] = option.cocotb_elab_args
        self.test_args: Sequence[str] = option.cocotb_test_args
        self.plusargs: Sequence[str] = option.cocotb_plusargs
        self.env: Mapping[str, str] = option.cocotb_env
        self.gui: bool = option.cocotb_gui
        self.pre_cmd: list[str] | None = option.cocotb_pre_cmd
        self.test_filter: str | None = option.cocotb_test_filter

        for marker in reversed(list(request.node.iter_markers("cocotb"))):
            for name, value in marker.kwargs.items():
                if hasattr(self, name):
                    setattr(self, name, value)

        if self.toplevel_lang == "auto":
            if self.simulator in ("verilator", "icarus"):
                self.toplevel_lang = "verilog"
            elif self.simulator in ("nvc", "ghdl"):
                self.toplevel_lang = "vhdl"
            else:
                self.toplevel_lang = None

        if not self.test_module:
            self.test_module = request.path.name.partition(".")[0]

        if not self.toplevel:
            if isinstance(self.test_module, str):
                self.toplevel = self.test_module
            else:
                self.toplevel = self.test_module[0]

            if self.toplevel.startswith("test_"):
                self.toplevel = self.toplevel.removeprefix("test_")

            elif self.toplevel.endswith("_test"):
                self.toplevel = self.toplevel.removesuffix("_test")

    @property
    def simulator(self) -> str:
        """Name of HDL simulator."""
        return str(self.runner.__class__.__name__).lower()

    def __setitem__(self, key: str, value: object) -> None:
        """Set HDL parameter/generic in HDL design."""
        self.parameters[key] = value

    def __getitem__(self, key: str) -> object:
        """Get HDL parameter/generic."""
        return self.parameters[key]

    def test(self) -> Path:
        """Build and test HDL design."""
        self.test_dir.mkdir(0o750, parents=True, exist_ok=True)
        results_xml: Path = self.test_dir / "results.xml"

        self.runner.build(
            hdl_library=self.library,
            sources=self.sources,
            includes=self.includes,
            defines=self.defines,
            parameters=self.parameters,
            build_args=self.build_args,
            hdl_toplevel=self.toplevel or None,
            always=self.always,
            build_dir=self.test_dir,
            cwd=self.test_dir,
            clean=self.clean,
            verbose=self.verbose,
            timescale=self.timescale,
            waves=self.waves,
        )

        return self.runner.test(
            test_module=self.test_module,
            hdl_toplevel=self.toplevel,
            hdl_toplevel_library=self.toplevel_library,
            hdl_toplevel_lang=self.toplevel_lang or None,
            gpi_interfaces=self.gpi_interfaces or None,
            testcase=self.testcase or None,
            seed=self.seed,
            elab_args=self.elab_args,
            test_args=self.test_args,
            plusargs=self.plusargs,
            extra_env=self.env,
            waves=self.waves,
            gui=self.gui,
            parameters=self.parameters or None,
            build_dir=self.test_dir,
            test_dir=self.test_dir,
            results_xml=results_xml,
            pre_cmd=self.pre_cmd or None,
            verbose=self.verbose,
            timescale=None if self.simulator in ("xcelium",) else self.timescale,
            test_filter=self.test_filter or None,
        )
