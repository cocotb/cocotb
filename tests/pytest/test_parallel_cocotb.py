# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import pytest
from test_cocotb import (
    compile_args,
    module_name,
    python_search,
    sim,
    sim_args,
    sim_build,
    toplevel,
    toplevel_lang,
    verilog_sources,
    vhdl_sources,
)

from cocotb.runner import get_runner


@pytest.mark.compile
def test_cocotb_parallel_compile():

    runner = get_runner(sim)()

    runner.build(
        always=True,
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        toplevel=toplevel,
        build_dir=sim_build,
        extra_args=compile_args,
    )


@pytest.mark.parametrize("seed", list(range(4)))
def test_cocotb_parallel(seed):

    runner = get_runner(sim)()

    runner.test(
        seed=seed,
        toplevel_lang=toplevel_lang,
        python_search=python_search,
        toplevel=toplevel,
        py_module=module_name,
        extra_args=sim_args,
        build_dir=sim_build,
    )
