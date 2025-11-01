# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Build and test HDL designs."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, MutableMapping, Sequence
from copy import deepcopy
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

    def __init__(self, request: FixtureRequest) -> None:
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
        self.includes: Sequence[PathLike] = []
        self.defines: Mapping[str, object] = {}
        self.parameters: MutableMapping[str, object] = {}
        self.build_args: Sequence[str | VHDL | Verilog] = []
        self.toplevel: str | None = None
        self.always: bool = option.cocotb_always
        self.clean: bool = option.cocotb_clean
        self.verbose: bool = option.cocotb_verbose
        self.timescale: tuple[str, str] | None = option.cocotb_timescale
        self.waves: bool = option.cocotb_waves

        # Test options
        self.test_module: str | Sequence[str] = ""
        self.toplevel_library: str = option.cocotb_toplevel_library
        self.gpi_interfaces: list[str] | None = option.cocotb_gpi_interfaces
        self.seed: str | int | None = option.cocotb_seed
        self.elab_args: Sequence[str] = []
        self.test_args: Sequence[str] = []
        self.plusargs: Sequence[str] = []
        self.env: Mapping[str, str] = {}
        self.gui: bool = option.cocotb_gui
        self.pre_cmd: list[str] | None = []

        # Store reference to command line options
        self._option = option

        for marker in reversed(list(request.node.iter_markers("cocotb"))):
            if marker.args:
                self.test_module = marker.args

            for name, value in marker.kwargs.items():
                if hasattr(self, name):
                    setattr(self, name, value)

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
        option = self._option

        self.test_dir.mkdir(0o750, parents=True, exist_ok=True)
        results_xml: Path = self.test_dir / "results.xml"

        # Allow to extend build, elab, test and + arguments from cli and configs
        build_args: Sequence[str] = self.build_args + option.cocotb_build_args
        elab_args: Sequence[str] = self.elab_args + option.cocotb_elab_args
        test_args: Sequence[str] = self.test_args + option.cocotb_test_args
        plusargs: Sequence[str] = self.plusargs + option.cocotb_plusargs
        includes: Sequence[str] = self.includes + option.cocotb_includes
        pre_cmd: list[str] = self.pre_cmd + option.cocotb_pre_cmd

        # Allow to override HDL parameters/generics, environment variables and defines from cli and configs
        parameters: dict[str, object] = dict(deepcopy(self.parameters))
        extra_env: dict[str, str] = dict(deepcopy(self.env))
        defines: dict[str, object] = dict(deepcopy(self.defines))

        parameters.update(option.cocotb_parameters)
        extra_env.update(option.cocotb_env)
        defines.update(option.cocotb_defines)

        self.runner.build(
            hdl_library=self.library,
            sources=self.sources,
            includes=includes,
            defines=defines,
            parameters=parameters,
            build_args=build_args,
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
            hdl_toplevel=self.toplevel or "",
            hdl_toplevel_library=self.toplevel_library,
            gpi_interfaces=self.gpi_interfaces or None,
            seed=self.seed,
            elab_args=elab_args,
            test_args=test_args,
            plusargs=plusargs,
            extra_env=extra_env,
            waves=self.waves,
            gui=self.gui,
            parameters=parameters or None,
            build_dir=self.test_dir,
            test_dir=self.test_dir,
            results_xml=str(results_xml),
            pre_cmd=pre_cmd or None,
            verbose=self.verbose,
            timescale=None if self.simulator in ("xcelium",) else self.timescale,
        )
