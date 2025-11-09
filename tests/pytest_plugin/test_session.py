# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Build HDL designs with different HDL modules at once during pytest session scope."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest import FixtureRequest, fixture

from cocotb_tools.pytest.hdl import HDL

DESIGNS: Path = Path(__file__).parent.parent.resolve() / "designs"


@fixture(name="my_hdl_project", scope="session")
def my_hdl_project_fixture(hdl_session: HDL, request: FixtureRequest) -> HDL:
    """Define HDL design with all HDL modules and build it."""
    # NOTE: Icarus/Xcelium runners are requiring a defined top level
    hdl_session.toplevel = "sample_module"

    # Selected based on command line argument --cocotb-toplevel-lang=<verilog|vhdl>
    # or enforced by HDL simulator choice --cocotb-simulator=<name>
    if hdl_session.toplevel_lang == "vhdl":
        hdl_session.sources = (
            DESIGNS / "array_module" / "array_module_pack.vhd",
            DESIGNS / "array_module" / "array_module.vhd",
            DESIGNS / "sample_module" / "sample_module_package.vhdl",
            DESIGNS / "sample_module" / "sample_module_1.vhdl",
            DESIGNS / "sample_module" / "sample_module.vhdl",
        )
    else:
        hdl_session.sources = (
            DESIGNS / "array_module" / "array_module.sv",
            DESIGNS / "sample_module" / "sample_module.sv",
        )

    if hdl_session.simulator == "questa":
        hdl_session.build_args = ["+acc"]

    elif hdl_session.simulator == "xcelium":
        hdl_session.build_args = ["-v93"]

    elif hdl_session.simulator == "nvc":
        hdl_session.build_args = ["--std=08"]

    hdl_session.build()

    return hdl_session


@fixture(name="array_module")
def array_module_fixture(hdl: HDL, my_hdl_project: HDL) -> HDL:
    """Define HDL module: ``array_module``."""
    hdl.build_dir = my_hdl_project.build_dir
    hdl.toplevel = "array_module"

    return hdl


@fixture(name="sample_module")
def sample_module_fixture(hdl: HDL, my_hdl_project: HDL) -> HDL:
    """Define HDL module: ``sample_module``."""
    hdl.build_dir = my_hdl_project.build_dir
    hdl.toplevel = "sample_module"

    return hdl


@pytest.mark.cocotb_runner
def test_array_module(array_module: HDL) -> None:
    """Run HDL simulator to test ``array_module``."""
    # TODO: Not all runners are supporting build_dir != test_dir :( For now, run only build stage
    # array_module.test()


@pytest.mark.cocotb_runner
def test_sample_module(sample_module: HDL) -> None:
    """Run HDL simulator to test ``sample_module``."""
    # TODO: Not all runners are supporting build_dir != test_dir :( For now, run only build stage
    # sample_module.test()
