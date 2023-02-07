# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys

import pytest
from test_cocotb import (
    compile_args,
    gpi_interfaces,
    hdl_toplevel,
    hdl_toplevel_lang,
    module_name,
    sim,
    sim_args,
    sim_build,
    tests_dir,
    verilog_sources,
    vhdl_sources,
)

from cocotb.runner import get_runner

pytestmark = pytest.mark.simulator_required
sys.path.insert(0, os.path.join(tests_dir, "pytest"))


@pytest.mark.compile
def test_cocotb_parallel_compile():

    runner = get_runner(sim)

    runner.build(
        always=True,
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        hdl_toplevel=hdl_toplevel,
        build_dir=sim_build,
        build_args=compile_args,
    )


@pytest.mark.parametrize("seed", list(range(4)))
def test_cocotb_parallel(seed):

    runner = get_runner(sim)

    runner.test(
        seed=seed,
        hdl_toplevel_lang=hdl_toplevel_lang,
        hdl_toplevel=hdl_toplevel,
        gpi_interfaces=gpi_interfaces,
        test_module=module_name,
        test_args=sim_args,
        build_dir=sim_build,
    )
