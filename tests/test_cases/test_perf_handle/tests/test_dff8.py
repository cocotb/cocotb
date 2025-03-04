# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import os
import sys
import time
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.runner import get_runner
from cocotb.triggers import RisingEdge

NUM_SAMPLES = int(os.environ.get("NUM_SAMPLES", 10000))
if cocotb.simulator.is_running():
    DATA_WIDTH = int(cocotb.top.DATA_WIDTH)


def test_dff8_runner():
    """
    Simulate the "dff8" example
    This file can be run directly or via pytest discovery.
    """
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    verilog_sources = []
    vhdl_sources = []
    build_args = []

    if hdl_toplevel_lang == "verilog":
        verilog_sources = [proj_path / "hdl" / "dff8.sv"]
        if sim in ["riviera", "activehdl"]:
            build_args = ["-sv2k12"]
    else:
        raise ValueError(
            f"A valid value verilog file was not provided for TOPLEVEL_LANG={hdl_toplevel_lang}"
        )

    parameters = {
        "DATA_WIDTH": "8",
    }

    # equivalent to setting the PYTHONPATH environment variable
    sys.path.append(str(proj_path / "tests"))

    runner = get_runner(sim)
    runner.build(
        hdl_toplevel="dff8",
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        build_args=build_args,
        parameters=parameters,
        always=True,
    )
    runner.test(
        hdl_toplevel="dff8",
        hdl_toplevel_lang=hdl_toplevel_lang,
        test_module="test_dff8",
    )


@cocotb.test()
async def test_dff8(dut):
    """
    Cocotb performance test. Measure how long it takes to access DUT's signals
    with different methods.

    The environment variable NUM_SAMPLES can be used to configure how many
    iterations are performed.

    DUT's signals:
        - clk_i
        - rst_i

        - d_i, 8-bit
        - q_o, 8-bit
        - nq_o, 8-bit

        - be_d_i, 8-bit
        - be_q_o, 8-bit
        - be_nq_o, 8-bit

    This test does not explicitly call BinaryValue or LogicArray. It
    can be used to compare multiple implementation together.
    """
    cocotb.start_soon(Clock(dut.clk_i, 10, units="us").start(start_high=False))

    dut._log.info("Initialize and reset model")

    dut.d_i.value = 0
    dut.be_d_i.value = 0

    # Reset sequence
    dut.rst_i.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk_i)
    dut.rst_i.value = 0

    # Little Endian, setting input signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        dut.d_i.value = i % 256
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Little Endian, setting input signal: {elapsed_time}s")
    await RisingEdge(dut.clk_i)

    # Big Endian, setting input signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        dut.be_d_i.value = i % 256
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Big Endian, setting input signal: {elapsed_time}s")
    await RisingEdge(dut.clk_i)

    # Little Endian, reading output signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        _ = dut.q_o.value
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Little Endian, reading the output signal: {elapsed_time}")
    await RisingEdge(dut.clk_i)

    # Big Endian, reading output signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        _ = dut.be_q_o.value
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Big Endian, reading the output signal: {elapsed_time}")
    await RisingEdge(dut.clk_i)

    # Little Endian, reading part of the output signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        _ = dut.q_o.value[0:6]  # BinaryValue requires indexes to be from low to high
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Little Endian, reading part of the output signal: {elapsed_time}")
    await RisingEdge(dut.clk_i)

    # Big Endian, reading part of the output signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        _ = dut.be_q_o.value[0:6]  # BinaryValue requires indexes to be from low to high
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Big Endian Endian, reading part of the output sign: {elapsed_time}")
    await RisingEdge(dut.clk_i)

    # Little Endian, reading single bit from the output signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        _ = dut.q_o.value[4]
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(
        f"Little Endian, reading single bit from the output signal: {elapsed_time}"
    )
    await RisingEdge(dut.clk_i)

    # Big Endian, reading single bit from the output signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        _ = dut.be_q_o.value[4]
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(
        f"Big Endian, reading single bit from the output signal: {elapsed_time}"
    )
    await RisingEdge(dut.clk_i)

    # Little Endian, setting part of the input signal
    # handle.py: Slice indexing is not supported
    await RisingEdge(dut.clk_i)
    raised_error = ""
    try:
        dut.d_i[6:0].value = 42
    except IndexError as e:
        raised_error = str(e)
    assert raised_error == "Slice indexing is not supported"
    dut._log.info("Little Endian, setting part of the input signal: Unsupported")

    # Big Endian, setting part of the input signal
    # handle.py: Slice indexing is not supported
    await RisingEdge(dut.clk_i)
    raised_error = ""
    try:
        dut.be_d_i[6:0].value = 42
    except IndexError as e:
        raised_error = str(e)
    assert raised_error == "Slice indexing is not supported"
    dut._log.info("Big Endian, setting part of the input signal: Unsupported")

    # Little Endian, setting single bit of the input signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        dut.d_i[4].value = i % 2
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(
        f"Little Endian, setting single bit of the input signal: {elapsed_time}"
    )
    await RisingEdge(dut.clk_i)

    # Big Endian, setting single bit of the input signal
    start_time = time.perf_counter()
    for i in range(NUM_SAMPLES):
        await RisingEdge(dut.clk_i)
        dut.be_d_i[4].value = i % 2
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Big Endian, setting single bit of the input signal: {elapsed_time}")
    await RisingEdge(dut.clk_i)

    # Little Endian, read + write signals
    start_time = time.perf_counter()
    dut.d_i.value = 0
    await RisingEdge(dut.clk_i)
    expected = 0
    for i in range(NUM_SAMPLES):
        # Set input signals
        val = i % 256
        dut.d_i.value = val
        await RisingEdge(dut.clk_i)
        # Check output signals on next cycle
        assert (
            dut.q_o.value == expected
        ), "signal Q should take the value of D after 1 cycle"
        expected = val
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Little Endian, read + write signals: {elapsed_time}")
    await RisingEdge(dut.clk_i)

    # Big Endian, read + write signals
    start_time = time.perf_counter()
    dut.be_d_i.value = 0
    await RisingEdge(dut.clk_i)
    expected = 0
    for i in range(NUM_SAMPLES):
        # Set input signals
        val = i % 256
        dut.be_d_i.value = val
        await RisingEdge(dut.clk_i)
        # Check output signals on next cycle
        assert (
            dut.be_q_o.value == expected
        ), "signal Q should take the value of D after 1 cycle"
        expected = val
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    dut._log.info(f"Big Endian, read + write signals: {elapsed_time}")
    await RisingEdge(dut.clk_i)


if __name__ == "__main__":
    test_dff8_runner()
