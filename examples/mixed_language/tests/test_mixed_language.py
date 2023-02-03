# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os
import sys
from pathlib import Path

import pytest

import cocotb
from cocotb.clock import Clock
from cocotb.runner import get_runner
from cocotb.triggers import RisingEdge, Timer


# Riviera fails to find dut.i_swapper_sv (gh-2921)
@cocotb.test(
    expect_error=AttributeError
    if cocotb.simulator.is_running()
    and cocotb.SIM_NAME.lower().startswith(("riviera", "aldec"))
    and cocotb.LANGUAGE == "vhdl"
    else ()
)
async def mixed_language_accessing_test(dut):
    """Try accessing handles and setting values in a mixed language environment."""
    await Timer(100, units="ns")

    verilog = dut.i_swapper_sv
    dut._log.info("Got: %s" % repr(verilog._name))

    # discover all attributes of the SV component
    # This is a workaround since SV modules are not discovered automatically
    # when using Modelsim/Questa and a VHDL toplevel file.
    verilog._discover_all()

    vhdl = dut.i_swapper_vhdl
    dut._log.info("Got: %s" % repr(vhdl._name))

    verilog.reset_n.value = 1
    await Timer(100, units="ns")

    vhdl.reset_n.value = 1
    await Timer(100, units="ns")

    assert int(verilog.reset_n) == int(vhdl.reset_n), "reset_n signals were different"

    # Try accessing an object other than a port...
    verilog.flush_pipe.value
    vhdl.flush_pipe.value


# Riviera fails to find dut.i_swapper_sv (gh-2921)
@cocotb.test(
    expect_error=AttributeError
    if cocotb.simulator.is_running()
    and cocotb.SIM_NAME.lower().startswith(("riviera", "aldec"))
    and cocotb.LANGUAGE == "vhdl"
    else ()
)
async def mixed_language_functional_test(dut):
    """Try concurrent simulation of VHDL and Verilog and check the output."""
    await Timer(100, units="ns")

    verilog = dut.i_swapper_sv
    dut._log.info("Got: %s" % repr(verilog._name))

    vhdl = dut.i_swapper_vhdl
    dut._log.info("Got: %s" % repr(vhdl._name))

    # setup default values
    dut.reset_n.value = 0
    dut.stream_out_ready.value = 1

    dut.stream_in_startofpacket.value = 0
    dut.stream_in_endofpacket.value = 0
    dut.stream_in_data.value = 0
    dut.stream_in_valid.value = 1
    dut.stream_in_empty.value = 0

    dut.csr_address.value = 0
    dut.csr_read.value = 0
    dut.csr_write.value = 0
    dut.csr_writedata.value = 0

    # reset cycle
    await Timer(100, units="ns")
    dut.reset_n.value = 1
    await Timer(100, units="ns")

    # start clock
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    await Timer(500, units="ns")

    previous_indata = 0
    # transmit some packets
    for _ in range(1, 5):

        for i in range(1, 11):
            await RisingEdge(dut.clk)
            previous_indata = dut.stream_in_data.value

            # write stream in data
            dut.stream_in_data.value = i + 0x81FFFFFF2B00  # generate a magic number
            dut.stream_in_valid.value = 1
            await RisingEdge(dut.clk)
            dut.stream_in_valid.value = 0

            # await stream out data
            await RisingEdge(dut.clk)
            await RisingEdge(dut.clk)

            # compare in and out data
            assert int(previous_indata) == int(
                dut.stream_out_data.value
            ), f"stream in data and stream out data were different in round {i}"


sim = os.getenv("SIM", "icarus")


@pytest.mark.skipif(
    sim in ["icarus", "ghdl", "verilator"],
    reason=f"Skipping example mixed_language since {sim} doesn't support this",
)
def test_mixed_language_runner():
    """Simulate the mixed_language example using the Python runner.

    This file can be run directly or via pytest discovery.
    """
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")

    proj_path = Path(__file__).resolve().parent.parent

    verilog_sources = [proj_path / "hdl" / "endian_swapper.sv"]
    vhdl_sources = [proj_path / "hdl" / "endian_swapper.vhdl"]

    if hdl_toplevel_lang == "verilog":
        verilog_sources += [proj_path / "hdl" / "toplevel.sv"]
    elif hdl_toplevel_lang == "vhdl":
        vhdl_sources += [proj_path / "hdl" / "toplevel.vhdl"]
    else:
        raise ValueError(
            f"A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG={hdl_toplevel_lang}"
        )

    test_args = []
    if sim == "xcelium":
        test_args = ["-v93"]
    elif sim == "questa":
        test_args = ["-t", "1ps"]

    # equivalent to setting the PYTHONPATH environment variable
    sys.path.append(str(proj_path / "tests"))

    runner = get_runner(sim)

    runner.build(
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        always=True,
    )

    runner.test(
        hdl_toplevel="endian_swapper_mixed",
        hdl_toplevel_lang=hdl_toplevel_lang,
        test_module="test_mixed_language",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_mixed_language_runner()
