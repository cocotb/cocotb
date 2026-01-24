# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Build and test HDL designs."""

from __future__ import annotations

import os
import re
from collections.abc import MutableMapping, MutableSequence
from pathlib import Path
from typing import Any, Callable

from pytest import FixtureRequest

from cocotb_tools.runner import (
    VHDL,
    PathLike,
    VerilatorControlFile,
    Verilog,
)

_POSIX_PATH: re.Pattern = re.compile(r"[^A-Za-z0-9/._-]")


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
        nodeid = _POSIX_PATH.sub("_", nodeid.replace(".py::", "/").replace("::", "/"))

        if os.path.sep != "/":
            nodeid = nodeid.replace("/", os.path.sep)

        self.request: FixtureRequest = request
        """The pytest fixture request."""

        self.test_dir: PathLike = Path(option.cocotb_build_dir).resolve() / nodeid
        """Directory to run the tests in."""

        self.simulator: str = option.cocotb_simulator
        """Name of HDL simulator."""

        # Build options
        self.library: str = option.cocotb_library
        """The library name to compile into."""

        self.sources: MutableSequence[
            PathLike | VHDL | Verilog | VerilatorControlFile
        ] = []
        """Language-agnostic list of source files to build."""

        self.includes: MutableSequence[PathLike] = option.cocotb_includes.copy()
        """Verilog include directories."""

        self.defines: MutableMapping[str, object] = option.cocotb_defines.copy()
        """Defines to set."""

        self.parameters: MutableMapping[str, object] = option.cocotb_parameters.copy()
        """Verilog parameters or VHDL generics."""

        self.build_args: MutableSequence[str | VHDL | Verilog] = (
            option.cocotb_build_args.copy()
        )
        """Extra build arguments for the simulator."""

        self._toplevel: str | None = None
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
        self.test_modules: MutableSequence[str] = []
        """Name(s) of the Python module(s) containing the tests to run."""

        self.toplevel_library: str = option.cocotb_toplevel_library
        """The library name for HDL toplevel module."""

        self.toplevel_lang: str = option.cocotb_toplevel_lang
        """Language of the HDL toplevel module."""

        self.gpi_interfaces: MutableSequence[str] = option.cocotb_gpi_interfaces.copy()
        """List of GPI interfaces to use, with the first one being the entry point."""

        self.seed: int | None = option.cocotb_seed
        """A specific random seed to use."""

        self.elab_args: MutableSequence[str] = option.cocotb_elab_args.copy()
        """A list of elaboration arguments for the simulator."""

        self.test_args: MutableSequence[str] = option.cocotb_test_args.copy()
        """A list of extra arguments for the simulator."""

        self.plusargs: MutableSequence[str] = option.cocotb_plusargs.copy()
        """'plusargs' to set for the simulator."""

        self.env: MutableMapping[str, str] = option.cocotb_env.copy()
        """Extra environment variables to set."""

        self.gui: bool = option.cocotb_gui
        """Run with simulator GUI."""

        self.pre_cmd: MutableSequence[str] = option.cocotb_pre_cmd.copy()
        """Commands to run before simulation begins. Typically Tcl commands for simulators that support them."""

        self._build_done: bool = False
        """Mark that the :meth:`cocotb_tools.pytest.hdl.HDL.build` method was called at least once."""

        self._apply_markers(request.node)

        if not self.test_modules and self.request.scope != "session":
            self.test_modules = [request.path.name.partition(".")[0]]

    def __setitem__(self, key: str, value: object) -> None:
        """Set HDL parameter/generic in HDL design."""
        self.parameters[key] = value

    def __getitem__(self, key: str) -> object:
        """Get HDL parameter/generic."""
        return self.parameters[key]

    @property
    def toplevel(self) -> str:
        """Name of the HDL toplevel module."""
        if self._toplevel:
            return self._toplevel

        if self.sources:
            # Path.stem can still return dots in case of <name>.<ext1>.<ext2>
            return Path(str(self.sources[-1])).name.partition(".")[0]

        if not self.test_modules:
            return ""

        # Test modules may contain dots: "a.b.test_module" -> "test_module"
        test_module: str = self.test_modules[0].rpartition(".")[2]

        if test_module.startswith("test_"):
            return test_module.removeprefix("test_")

        if test_module.endswith("_test"):
            return test_module.removesuffix("_test")

        return test_module

    @toplevel.setter
    def toplevel(self, toplevel: str) -> None:
        self._toplevel = toplevel

    def build(self) -> None:
        """Build a HDL design.

        It will delegate building HDL design to :func:`~cocotb_tools.pytest.hookspecs.pytest_cocotb_hdl_build` hook.

        The default implementation of hook is invoking the :meth:`cocotb_tools.runner.Runner.build` method.
        """
        # Delegate building HDL design to external hooks
        self.request.node.ihook.pytest_cocotb_hdl_build(hdl=self)

        # Used to invoke the build method implicitly
        self._build_done = True

    def test(self) -> None:
        """Test a HDL design.

        It will delegate testing HDL design to :func:`~cocotb_tools.pytest.hookspecs.pytest_cocotb_hdl_test` hook.

        The default implementation of hook is invoking the :meth:`cocotb_tools.runner.Runner.test` method.

        .. note::

            If the :meth:`~cocotb_tools.pytest.hdl.HDL.build` method was not called explicitly, then it will be
            invoked implicitly by this method.
        """
        # Invoke the build method implicitly
        if not self._build_done:
            self.build()

        # Delegate testing HDL design to external hooks
        self.request.node.ihook.pytest_cocotb_hdl_test(hdl=self)

    def _apply_markers(self, node: Any) -> None:
        """Apply all cocotb markers starting from the root (session) to the leaf (test function).

        * Markers with positional arguments are extending targeted attribute.
        * Markers with named arguments are updating targeted attribute.

        Args:
            node: The pytest node (session, package, module, class, function, ...).
        """
        for parent in reversed(list(node.iter_parents())):
            for marker in parent.own_markers:
                name: str = marker.name

                if name.startswith("cocotb_"):
                    apply: Callable[..., None] | None = getattr(
                        self, f"_mark_{name}", None
                    )

                    if apply:
                        apply(*marker.args, **marker.kwargs)

    def _mark_cocotb_runner(self, test_module: str = "", *args: str) -> None:
        self.test_modules = [test_module, *args] if test_module else list(args)

    def _mark_cocotb_sources(
        self, *args: PathLike | Verilog | VHDL | VerilatorControlFile
    ) -> None:
        self.sources.extend(args)

    def _mark_cocotb_defines(self, **kwargs: object) -> None:
        self.defines.update(kwargs)

    def _mark_cocotb_parameters(self, **kwargs: object) -> None:
        self.parameters.update(kwargs)

    def _mark_cocotb_env(self, **kwargs: str) -> None:
        self.env.update(kwargs)

    def _mark_cocotb_includes(self, *args: PathLike) -> None:
        self.includes.extend(args)

    def _mark_cocotb_plusargs(self, *args: str) -> None:
        self.plusargs.extend(args)

    def _mark_cocotb_timescale(self, unit: str, precision: str | None = None) -> None:
        self.timescale = (unit, precision if precision else unit)

    def _mark_cocotb_seed(self, value: int) -> None:
        self.seed = value

    def _mark_cocotb_build_args(self, *args: str | VHDL | Verilog) -> None:
        self.build_args.extend(args)

    def _mark_cocotb_elab_args(self, *args: str) -> None:
        self.elab_args.extend(args)

    def _mark_cocotb_test_args(self, *args: str) -> None:
        self.test_args.extend(args)

    def _mark_cocotb_pre_cmd(self, *args: str) -> None:
        self.pre_cmd.extend(args)

    def _mark_cocotb_library(self, name: str) -> None:
        self.library = name

    def _mark_cocotb_waves(self, condition: bool = True) -> None:
        self.waves = condition

    def _mark_cocotb_verbose(self, condition: bool = True) -> None:
        self.verbose = condition

    def _mark_cocotb_always(self, condition: bool = True) -> None:
        self.always = condition

    def _mark_cocotb_clean(self, condition: bool = True) -> None:
        self.clean = condition
