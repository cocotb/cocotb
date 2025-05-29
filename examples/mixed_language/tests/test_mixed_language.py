# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os
import sys
from pathlib import Path

import pytest

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb_tools.runner import get_runner

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


# Riviera fails to find dut.i_swapper_sv (gh-2921)
@cocotb.test(
    expect_error=AttributeError
    if cocotb.simulator.is_running()
    and cocotb.SIM_NAME.lower().startswith(("riviera", "aldec"))
    and LANGUAGE == "vhdl"
    else ()
)
async def mixed_language_accessing_test(dut):
    """Try accessing handles and setting values in a mixed language environment."""
    await Timer(100, unit="ns")

    verilog = dut.i_swapper_sv
    dut._log.info(f"Got: {verilog._name!r}")

    # discover all attributes of the SV component
    # This is a workaround since SV modules are not discovered automatically
    # when using Modelsim/Questa and a VHDL toplevel file.
    verilog._discover_all()

    vhdl = dut.i_swapper_vhdl
    dut._log.info(f"Got: {vhdl._name!r}")

    verilog.reset_n.value = 1
    await Timer(100, unit="ns")

    vhdl.reset_n.value = 1
    await Timer(100, unit="ns")

    assert verilog.reset_n.value == vhdl.reset_n.value, "reset_n signals were different"

    # Try accessing an object other than a port...
    verilog.flush_pipe.value
    vhdl.flush_pipe.value


# Riviera fails to find dut.i_swapper_sv (gh-2921)
@cocotb.test(
    expect_error=AttributeError
    if cocotb.simulator.is_running()
    and cocotb.SIM_NAME.lower().startswith(("riviera", "aldec"))
    and LANGUAGE == "vhdl"
    else ()
)
async def mixed_language_functional_test(dut):
    """Try concurrent simulation of VHDL and Verilog and check the output."""
    await Timer(100, unit="ns")

    verilog = dut.i_swapper_sv
    dut._log.info(f"Got: {verilog._name!r}")

    vhdl = dut.i_swapper_vhdl
    dut._log.info(f"Got: {vhdl._name!r}")

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
    await Timer(100, unit="ns")
    dut.reset_n.value = 1
    await Timer(100, unit="ns")

    # start clock
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await Timer(500, unit="ns")

    previous_indata = 0
    # transmit some packets
    for _ in range(1, 5):
        for i in range(1, 11):
            await RisingEdge(dut.clk)
            previous_indata = dut.stream_in_data.value.to_unsigned()

            # write stream in data
            dut.stream_in_data.value = i + 0x81FFFFFF2B00  # generate a magic number
            dut.stream_in_valid.value = 1
            await RisingEdge(dut.clk)
            dut.stream_in_valid.value = 0

            # await stream out data
            await RisingEdge(dut.clk)
            await RisingEdge(dut.clk)

            # compare in and out data
            assert previous_indata == dut.stream_out_data.value.to_unsigned(), (
                f"stream in data and stream out data were different in round {i}"
            )


sim = os.getenv("SIM", "icarus")


@pytest.mark.skipif(
    sim not in ["questa", "riviera", "xcelium"],
    reason=f"Skipping example mixed_language since {sim} doesn't support this",
)
def test_mixed_language_runner():
    """Simulate the mixed_language example using the Python runner.

    This file can be run directly or via pytest discovery.
    """
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")

    proj_path = Path(__file__).resolve().parent.parent

    sources = [
        proj_path / "hdl" / "endian_swapper.sv",
        proj_path / "hdl" / "endian_swapper.vhdl",
    ]

    if hdl_toplevel_lang == "verilog":
        sources += [proj_path / "hdl" / "toplevel.sv"]
    elif hdl_toplevel_lang == "vhdl":
        sources += [proj_path / "hdl" / "toplevel.vhdl"]
    else:
        raise ValueError(
            f"A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG={hdl_toplevel_lang}"
        )

    build_args = []
    test_args = []
    if sim == "xcelium":
        build_args = ["-v93"]
    elif sim == "questa":
        test_args = ["-t", "1ps"]

    # equivalent to setting the PYTHONPATH environment variable
    sys.path.append(str(proj_path / "tests"))

    runner = get_runner(sim)

    runner.build(
        hdl_toplevel="endian_swapper_mixed",
        sources=sources,
        always=True,
        build_args=build_args,
    )

    runner.test(
        hdl_toplevel="endian_swapper_mixed",
        hdl_toplevel_lang=hdl_toplevel_lang,
        test_module="test_mixed_language",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_mixed_language_runner()
