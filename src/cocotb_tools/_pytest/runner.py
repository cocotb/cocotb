# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Fixture request for the :class:`cocotb_tools.runner.Runner` class."""

from __future__ import annotations

import re
from argparse import Namespace
from collections.abc import Mapping, Sequence
from pathlib import Path
from shutil import which

from pytest import FixtureRequest, Module

from cocotb_tools.runner import (
    SUPPORTED_RUNNERS,
    VHDL,
    PathLike,
    Runner,
    VerilatorControlFile,
    Verilog,
    _Command,
    get_runner,
)

#: POSIX compatible filename paths: 0-9, A-Z, a-z, _, ., -
_POSIX: re.Pattern[str] = re.compile(r"[^\w.-]")

#: Map name of runner to simulation command
_RUNNER_TO_COMMAND: dict[str, str] = {
    "icarus": "iverilog",
    "xcelium": "xrun",
    "questa": "vsim",
    "riviera": "vsimsa",
    "activehdl": "vsimsa",
}


class FixtureRunner(Runner):
    """Fixture request for the :class:`cocotb_tools.runner.Runner` instance."""

    def __init__(self, request: FixtureRequest) -> None:
        """Create a new instance of the runner."""

        self.option: Namespace = request.config.option
        """Plugin configuration options from configuration files and command line arguments."""

        simulator: str = self.option.cocotb_simulator

        if not simulator:
            simulator = _find_simulator(language=self.option.cocotb_toplevel_lang)

        self.instance: Runner = get_runner(simulator)
        """Instance of the :class:`cocotb_tools.runner.Runner` class."""

        path: Path = _to_relative_path(request.node.path)

        self.build_dir: Path = (
            self.option.cocotb_build_dir.resolve() / path.parent / path.stem
        )
        """Path to directory to run the build step in. Based on defined DUT fixture."""

        if hasattr(request, "param"):
            self.build_dir /= _POSIX.sub("_", str(request.param)).strip("_")

        self.test_dir: Path = self.build_dir
        """Path to directory to run the tests in. Defaults to *build_dir*."""

        self.cwd: Path = self.build_dir
        """Path to directory to execute the build command(s) in. Defaults to *build_dir*."""

        self.test_modules: list[str] = []
        """Name(s) of the Python module(s) containing the tests to run."""

        self.hdl_toplevel: str = ""
        """The name of the HDL toplevel module."""

        self.supported_gpi_interfaces = self.instance.supported_gpi_interfaces

        module: Module | None = request.node.getparent(Module)

        if module:
            self.test_modules.append(module.getmodpath(includemodule=True))

    def build(
        self,
        hdl_library: str = "",
        verilog_sources: Sequence[PathLike | Verilog] = [],
        vhdl_sources: Sequence[PathLike | VHDL] = [],
        sources: Sequence[PathLike | VHDL | Verilog | VerilatorControlFile] = [],
        includes: Sequence[PathLike] = [],
        defines: Mapping[str, object] = {},
        parameters: Mapping[str, object] = {},
        build_args: Sequence[str | VHDL | Verilog] = [],
        hdl_toplevel: str | None = None,
        always: bool = False,
        build_dir: PathLike = "",
        cwd: PathLike | None = None,
        clean: bool = False,
        verbose: bool = False,
        timescale: tuple[str, str] | None = None,
        waves: bool = False,
        log_file: PathLike | None = None,
    ) -> None:
        __tracebackhide__ = True

        option = self.option

        if hdl_toplevel:
            self.hdl_toplevel = hdl_toplevel

        self.instance.build(
            hdl_library=hdl_library or option.cocotb_library,
            verilog_sources=verilog_sources,
            vhdl_sources=vhdl_sources,
            sources=sources,
            includes=includes + option.cocotb_includes,
            defines=defines | option.cocotb_defines,
            parameters=parameters | option.cocotb_parameters,
            build_args=build_args + option.cocotb_build_args,
            hdl_toplevel=hdl_toplevel,
            always=always or option.cocotb_always,
            build_dir=build_dir or self.build_dir,
            cwd=cwd or self.cwd,
            clean=clean or option.cocotb_clean,
            verbose=verbose or option.cocotb_verbose,
            timescale=timescale or option.cocotb_timescale or None,
            waves=waves or option.cocotb_waves,
            log_file=log_file,
        )

    def test(
        self,
        test_module: str | Sequence[str] = "",
        hdl_toplevel: str = "",
        hdl_toplevel_library: str = "",
        hdl_toplevel_lang: str | None = None,
        gpi_interfaces: list[str] | None = None,
        testcase: str | Sequence[str] | None = None,
        seed: str | int | None = None,
        elab_args: Sequence[str] = [],
        test_args: Sequence[str] = [],
        plusargs: Sequence[str] = [],
        extra_env: Mapping[str, str] = {},
        waves: bool = False,
        gui: bool = False,
        parameters: Mapping[str, object] | None = None,
        build_dir: PathLike | None = None,
        test_dir: PathLike | None = None,
        results_xml: str | None = None,
        pre_cmd: list[str] | None = None,
        verbose: bool = False,
        timescale: tuple[str, str] | None = None,
        log_file: PathLike | None = None,
        test_filter: str | None = None,
    ) -> Path:
        __tracebackhide__ = True

        option = self.option

        return self.instance.test(
            test_module=test_module or self.test_modules,
            hdl_toplevel=hdl_toplevel or self.hdl_toplevel,
            hdl_toplevel_lang=self.instance._check_hdl_toplevel_lang(
                hdl_toplevel_lang or option.cocotb_toplevel_lang or None
            ),
            hdl_toplevel_library=hdl_toplevel_library or option.cocotb_toplevel_library,
            gpi_interfaces=gpi_interfaces or option.cocotb_gpi_interfaces or None,
            testcase=testcase,
            seed=seed or option.cocotb_seed or None,
            elab_args=elab_args + option.cocotb_elab_args,
            test_args=test_args + option.cocotb_test_args,
            plusargs=plusargs + option.cocotb_plusargs,
            extra_env=extra_env | option.cocotb_env,
            waves=waves or option.cocotb_waves,
            gui=gui or option.cocotb_gui,
            parameters=(parameters or {}) | option.cocotb_parameters,
            build_dir=build_dir or self.build_dir,
            test_dir=test_dir or self.test_dir,
            results_xml=results_xml,
            pre_cmd=((pre_cmd or []) + option.cocotb_pre_cmd) or None,
            verbose=verbose or option.cocotb_verbose,
            timescale=timescale or option.cocotb_timescale or None,
            log_file=log_file,
            test_filter=test_filter,
        )

    def __call__(self) -> None:
        """Run simulation."""
        self.test()

    def _simulator_in_path(self) -> None:
        self.instance._simulator_in_path()

    def _build_command(self) -> Sequence[_Command]:
        return self.instance._build_command()

    def _test_command(self) -> Sequence[_Command]:
        return self.instance._test_command()

    def _get_include_options(self, includes: Sequence[PathLike]) -> _Command:
        return self.instance._get_include_options(includes)

    def _get_define_options(self, defines: Mapping[str, object]) -> _Command:
        return self.instance._get_define_options(defines)

    def _get_parameter_options(self, parameters: Mapping[str, object]) -> _Command:
        return self._get_parameter_options(parameters)


def _to_relative_path(path: Path) -> Path:
    """Try to convert provided path to relative path.

    Args:
        path: Path to convert.

    Returns:
        Relative path to current working directory.
    """
    if path.is_absolute():
        try:
            path = path.relative_to(Path.cwd())
        except ValueError:
            pass

    return path


def _find_simulator(language: str | None = None) -> str:
    """Try to find simulator in current environment (host, container, CI, ...).

    Args:
        language: Name of language like ``verilog`` or ``vhdl`` as hint when searching for simulator.

    Returns:
        Name of founded simulator. If not, it returns an empty string.
    """
    for name, runner in SUPPORTED_RUNNERS.items():
        if language and language not in runner.supported_gpi_interfaces:
            continue

        if which(_RUNNER_TO_COMMAND.get(name, name)):
            return name

    return ""
