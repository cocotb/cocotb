from __future__ import annotations

import sys
from types import SimpleNamespace

from cocotb_tools import sim_versions
from cocotb_tools.sim_versions import (
    GhdlVersion,
    IcarusVersion,
    NvcVersion,
    QuestaVersion,
    VerilatorVersion,
    VcsVersion,
    XceliumVersion,
)


def test_icarus_commandline_preserves_devel_tag() -> None:
    version = IcarusVersion.from_commandline(
        "Icarus Verilog version 12.0 (devel)\n\nCopyright ..."
    )

    assert version == IcarusVersion("12.0 (devel)")
    assert version < IcarusVersion("12.0")


def test_verilator_commandline_ignores_extra_revision_text() -> None:
    version = VerilatorVersion.from_commandline(
        "Verilator 5.041 devel rev v5.040-1-g4eb030717"
    )

    assert version == VerilatorVersion("5.041 devel")
    assert version >= VerilatorVersion("5.040")


def test_verilator_sim_version_ignores_release_date() -> None:
    assert VerilatorVersion("5.046 2025-04-06 rev v5.046") == VerilatorVersion(
        "5.046"
    )


def test_questa_comparison_uses_public_version_component() -> None:
    assert QuestaVersion("10.7c 2018.08") > QuestaVersion("10.7b 2018.06")
    assert QuestaVersion("2020.1 2020.01") == QuestaVersion("2020.1")
    assert QuestaVersion("2023.1_2 2023.03") > QuestaVersion("2023.1_1")


def test_vcs_letter_train_is_compared_before_date() -> None:
    assert VcsVersion("Q-2020.03-1_Full64") > VcsVersion("K-2015.09_Full64")


def test_xcelium_patch_comparison_is_numeric() -> None:
    assert XceliumVersion("24.03-s010") > XceliumVersion("24.03-s004")


def test_ghdl_dev_release_sorts_before_final_release() -> None:
    assert GhdlVersion("5.2.0-dev") < GhdlVersion("5.2")


def test_nvc_from_sim_version_uses_argument_or_cocotb_value(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "cocotb", SimpleNamespace(SIM_VERSION="1.18.2"))
    assert NvcVersion.from_sim_version() == NvcVersion("1.18.2")
    assert NvcVersion.from_sim_version("1.16.0") == NvcVersion("1.16")


def test_from_commandline_without_output_runs_the_version_command(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        assert args == (["verilator", "--version"],)
        assert kwargs["check"] is True
        assert kwargs["text"] is True
        return SimpleNamespace(stdout="Verilator 5.046 2025-04-06 rev v5.046\n")

    monkeypatch.setattr(sim_versions.subprocess, "run", fake_run)

    assert VerilatorVersion.from_commandline() == VerilatorVersion("5.046")
