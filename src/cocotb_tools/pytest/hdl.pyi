# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from collections.abc import Mapping, Sequence
from pathlib import Path

from cocotb_tools.runner import VHDL, PathLike, VerilatorControlFile, Verilog

class HDL:
    def build(
        self,
        hdl_library: str = "top",
        verilog_sources: Sequence[PathLike | Verilog] = [],
        vhdl_sources: Sequence[PathLike | VHDL] = [],
        sources: Sequence[PathLike | VHDL | Verilog | VerilatorControlFile] = [],
        includes: Sequence[PathLike] = [],
        defines: Mapping[str, object] = {},
        parameters: Mapping[str, object] = {},
        build_args: Sequence[str | VHDL | Verilog] = [],
        hdl_toplevel: str | None = None,
        always: bool = False,
        build_dir: PathLike = "sim_build",
        cwd: PathLike | None = None,
        clean: bool = False,
        verbose: bool = False,
        timescale: tuple[str, str] | None = None,
        waves: bool = False,
        log_file: PathLike | None = None,
    ) -> None: ...
    def test(
        self,
        test_module: str | Sequence[str] = "",
        hdl_toplevel: str = "",
        hdl_toplevel_library: str = "top",
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
    ) -> Path: ...
