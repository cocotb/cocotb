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
        """Create new instance of HDL design.

        Args:
            request: The pytest fixture request.
        """
        option = request.config.option
        nodeid: str = request.node.nodeid

        # Use only allowed characters by POSIX standard
        # Pytest is always using "/" as path separator regardless of current OS environment
        nodeid = POSIX_PATH.sub("_", nodeid.replace(".py::", "/").replace("::", "/"))

        if os.path.sep != "/":
            nodeid = nodeid.replace("/", os.path.sep)

        self.test_dir: PathLike = Path(option.cocotb_build_dir).resolve() / nodeid
        """Directory to run the tests in."""

        self.runner: Runner = get_runner(get_simulator(request.config))
        """Instance that allows to build HDL and run cocotb tests."""

        # Build options
        self.library: str = option.cocotb_library
        """The library name to compile into."""

        self.sources: Sequence[PathLike | VHDL | Verilog | VerilatorControlFile] = []
        """Language-agnostic list of source files to build."""

        self.includes: Sequence[PathLike] = []
        """Verilog include directories."""

        self.defines: Mapping[str, object] = {}
        """Defines to set."""

        self.parameters: MutableMapping[str, object] = {}
        """Verilog parameters or VHDL generics."""

        self.build_args: Sequence[str | VHDL | Verilog] = []
        """Extra build arguments for the simulator."""

        self.toplevel: str | None = None
        """Name of the HDL toplevel module."""

        self.always: bool = option.cocotb_always
        """Always run the build step."""

        self.clean: bool = option.cocotb_clean
        """Delete *build_dir* before building."""

        self.verbose: bool = option.cocotb_verbose
        """Enable verbose messages."""

        self.timescale: tuple[str, str] | None = option.cocotb_timescale
        """Tuple containing time unit and time precision for simulation."""

        self.waves: bool = option.cocotb_waves
        """Record signal traces."""

        self.build_dir: PathLike = self.test_dir
        """Directory to run the build step in."""

        self.cwd: PathLike = self.build_dir
        """Directory to execute the build command(s) in."""

        # Test options
        self.test_module: str | Sequence[str] = ""
        """Name(s) of the Python module(s) containing the tests to run."""

        self.toplevel_library: str = option.cocotb_toplevel_library
        """The library name for HDL toplevel module."""

        self.gpi_interfaces: list[str] | None = option.cocotb_gpi_interfaces
        """List of GPI interfaces to use, with the first one being the entry point."""

        self.seed: str | int | None = option.cocotb_seed
        """A specific random seed to use."""

        self.elab_args: Sequence[str] = []
        """A list of elaboration arguments for the simulator."""

        self.test_args: Sequence[str] = []
        """A list of extra arguments for the simulator."""

        self.plusargs: Sequence[str] = []
        """'plusargs' to set for the simulator."""

        self.env: Mapping[str, str] = {}
        """Extra environment variables to set."""

        self.gui: bool = option.cocotb_gui
        """Run with simulator GUI."""

        self.pre_cmd: list[str] | None = []
        """Commands to run before simulation begins. Typically Tcl commands for simulators that support them."""

        # Store reference to command line options
        self._option = option

        for marker in reversed(list(request.node.iter_markers("cocotb"))):
            if marker.args:
                self.test_module = marker.args

            for name, value in marker.kwargs.items():
                if not name.startswith("_") and hasattr(self, name):
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

    def build(
        self,
        library: str | None = None,
        sources: Sequence[PathLike | VHDL | Verilog | VerilatorControlFile]
        | None = None,
        includes: Sequence[PathLike] | None = None,
        defines: Mapping[str, object] | None = None,
        parameters: MutableMapping[str, object] | None = None,
        build_args: Sequence[str | VHDL | Verilog] | None = None,
        toplevel: str | None = None,
        always: bool = False,
        clean: bool = False,
        verbose: bool = False,
        timescale: tuple[str, str] | None = None,
        waves: bool = False,
        build_dir: PathLike | None = None,
        cwd: PathLike | None = None,
    ) -> None:
        """Build HDL design.

        Args:
            library:
                The library name to compile into.

            sources:
                Language-agnostic list of source files to build.

            includes:
                Verilog include directories.

            defines:
                Defines to set.

            parameters:
                Verilog parameters or VHDL generics.

            build_args:
                Extra build arguments for the simulator.

            toplevel:
                Name of the HDL toplevel module.

            always:
                Always run the build step.

            clean:
                Delete *build_dir* before building.

            verbose:
                Enable verbose messages.

            timescale:
                Tuple containing time unit and time precision for simulation.

            waves:
                Record signal traces.

            build_dir:
                Directory to run the build step in.

            cwd:
                Directory to execute the build command(s) in.
        """
        option = self._option

        build_dir = build_dir or self.build_dir
        Path(build_dir).mkdir(0o755, parents=True, exist_ok=True)

        # Allow to extend build, elab, test and + arguments from cli and configs
        build_args = (build_args or self.build_args) + option.cocotb_build_args
        includes = (includes or self.includes) + option.cocotb_includes

        # Allow to override HDL parameters/generics, environment variables and defines from cli and configs
        parameters = dict(deepcopy(parameters or self.parameters))
        defines = dict(deepcopy(defines or self.defines))

        parameters.update(option.cocotb_parameters)
        defines.update(option.cocotb_defines)

        self.runner.build(
            hdl_library=library or self.library,
            sources=sources or self.sources,
            includes=includes,
            defines=defines,
            parameters=parameters,
            build_args=build_args,
            hdl_toplevel=toplevel or self.toplevel or None,
            always=always or self.always,
            build_dir=build_dir,
            cwd=cwd or build_dir,
            clean=clean or self.clean,
            verbose=verbose or self.verbose,
            timescale=timescale or self.timescale,
            waves=waves or self.waves,
        )

    def test(
        self,
        test_module: str | Sequence[str] | None = None,
        toplevel: str | None = None,
        toplevel_library: str | None = None,
        gpi_interfaces: list[str] | None = None,
        parameters: MutableMapping[str, object] | None = None,
        seed: str | int | None = None,
        elab_args: Sequence[str] | None = None,
        test_args: Sequence[str] | None = None,
        plusargs: Sequence[str] | None = None,
        env: Mapping[str, str] | None = None,
        gui: bool = False,
        waves: bool = False,
        verbose: bool = False,
        pre_cmd: list[str] | None = None,
        timescale: tuple[str, str] | None = None,
        build_dir: PathLike | None = None,
        test_dir: PathLike | None = None,
    ) -> Path:
        """Test HDL design.

        Args:
            test_module:
                Name(s) of the Python module(s) containing the tests to run.

            toplevel:
                Name of the HDL toplevel module.

            toplevel_library:
                The library name for HDL toplevel module.

            gpi_interfaces:
                List of GPI interfaces to use, with the first one being the entry point.

            parameters:
                Verilog parameters or VHDL generics.

            seed:
                A specific random seed to use.

            elab_args:
                A list of elaboration arguments for the simulator.

            test_args:
                A list of extra arguments for the simulator.

            plusargs:
                'plusargs' to set for the simulator.

            env:
                Extra environment variables to set.

            gui:
                Run with simulator GUI.

            waves:
                Record signal traces.

            verbose:
                Enable verbose messages.

            pre_cmd:
                Commands to run before simulation begins. Typically Tcl commands for simulators that support them.

            timescale:
                Tuple containing time unit and time precision for simulation.

            build_dir:
                Directory to run the build step in.

            test_dir:
                Directory to run the tests in.

        Returns:
            Path to created results file with cocotb tests in JUnit XML format.
        """
        option = self._option

        build_dir = build_dir or self.build_dir
        Path(build_dir).mkdir(0o755, parents=True, exist_ok=True)

        test_dir = test_dir or self.test_dir
        Path(test_dir).mkdir(0o755, parents=True, exist_ok=True)

        results_xml: Path = Path(test_dir) / "results.xml"

        # Allow to extend build, elab, test and + arguments from cli and configs
        elab_args = (elab_args or self.elab_args) + option.cocotb_elab_args
        test_args = (test_args or self.test_args) + option.cocotb_test_args
        plusargs = (plusargs or self.plusargs) + option.cocotb_plusargs
        pre_cmd = (pre_cmd or self.pre_cmd) + option.cocotb_pre_cmd
        timescale = timescale or option.cocotb_timescale

        # Allow to override HDL parameters/generics, environment variables and defines from cli and configs
        parameters = dict(deepcopy(parameters or self.parameters))
        extra_env: dict[str, str] = dict(deepcopy(env or self.env))

        parameters.update(option.cocotb_parameters)
        extra_env.update(option.cocotb_env)

        return self.runner.test(
            test_module=test_module or self.test_module,
            hdl_toplevel=toplevel or self.toplevel or "",
            hdl_toplevel_library=toplevel_library or self.toplevel_library,
            gpi_interfaces=gpi_interfaces or self.gpi_interfaces or None,
            seed=seed or self.seed,
            elab_args=elab_args,
            test_args=test_args,
            plusargs=plusargs,
            extra_env=extra_env,
            waves=waves or self.waves,
            gui=gui or self.gui,
            parameters=parameters or None,
            build_dir=build_dir,
            test_dir=test_dir,
            results_xml=str(results_xml),
            pre_cmd=pre_cmd or None,
            verbose=verbose or self.verbose,
            timescale=None if self.simulator in ("xcelium",) else timescale,
        )
