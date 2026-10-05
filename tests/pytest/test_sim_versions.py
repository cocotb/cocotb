# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from cocotb_tools import sim_versions
from cocotb_tools.sim_versions import (
    ActivehdlVersion,
    GhdlVersion,
    IcarusVersion,
    ModelsimVersion,
    NvcVersion,
    QuestaVersion,
    VcsVersion,
    VerilatorVersion,
    XceliumVersion,
)


def test_activehdl_letter_suffix_does_not_crash():
    assert ActivehdlVersion("10.5a.12.6914") > ActivehdlVersion("10.5.216.6767")
    assert ActivehdlVersion("10.5a.12.6914") > ActivehdlVersion("10.5.12.6914")


def test_ghdl_dev_release_is_before_final_release():
    assert GhdlVersion("2.0.0-dev") < GhdlVersion("2.0.0")
    assert GhdlVersion("2.0.0-dev") < "2.0.0"
    assert GhdlVersion("4.1.0 (v4.1.0) [Some edition]") > GhdlVersion("4.0.0")


def test_icarus_from_commandline_parses_existing_output():
    cmdline = "Icarus Verilog version 12.0 (stable)\n\nCopyright ..."
    assert IcarusVersion.from_commandline(cmdline) == IcarusVersion("12.0")


def test_verilator_from_commandline_parses_existing_output():
    cmdline = "Verilator 5.041 devel rev v5.040-1-g4eb030717\n"
    assert VerilatorVersion.from_commandline(cmdline) == VerilatorVersion("5.041")


def test_modelsim_from_commandline_skips_arch_number():
    cmdline = "Model Technology ModelSim-64 vsim 10.7c Compiler 2018.08\n"
    assert ModelsimVersion.from_commandline(cmdline) == ModelsimVersion("10.7c")


def test_questa_from_commandline_skips_arch_number():
    cmdline = "QuestaSim-64 vsim 2023.1_2 Compiler 2023.03 Mar 13 2023\n"
    assert QuestaVersion.from_commandline(cmdline) == QuestaVersion("2023.1_2")


def test_xcelium_from_commandline_skips_xrun_prefix():
    cmdline = "xrun(64): 24.03-s010 (Release candidate)\n"
    assert XceliumVersion.from_commandline(cmdline) == XceliumVersion("24.03-s010")


def test_vcs_from_commandline_parses_current_ci_style_version():
    cmdline = "Synopsys VCS simulator X-2025.06_Full64\n"
    assert VcsVersion.from_commandline(cmdline) == VcsVersion("X-2025.06_Full64")


def test_vcs_mixed_format_ordering():
    assert VcsVersion("2023.03_Full64") > VcsVersion("Q-2020.03-1_Full64")


def test_empty_commandline_output_raises_valueerror():
    with pytest.raises(ValueError, match="empty output"):
        IcarusVersion.from_commandline("   ")


def test_from_commandline_without_argument_runs_version_command(monkeypatch):
    def run(cmd, **kwargs):
        assert cmd == ["nvc", "--version"]
        return SimpleNamespace(stdout="nvc 1.18.2\n")

    monkeypatch.setattr(sim_versions.subprocess, "run", run)
    assert NvcVersion.from_commandline() == NvcVersion("1.18.2")


def test_from_sim_version_uses_explicit_string():
    assert NvcVersion.from_sim_version("1.18.2") == NvcVersion("1.18.2")


def test_from_sim_version_reads_cocotb_sim_version(monkeypatch):
    monkeypatch.setitem(sys.modules, "cocotb", SimpleNamespace(SIM_VERSION="1.18.2"))
    assert NvcVersion.from_sim_version() == NvcVersion("1.18.2")
