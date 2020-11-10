# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer

MAXCOUNT = 123456

"""
In this example, the testbench is split into
an HDL part and a Python part.

We call our HDL ``TOPLEVEL`` ``tb_hdl`` here
to make clear it's the HDL part of the testbench
(as implemented in ``tb.sv``/``tb.vhdl``).
``TOPLEVEL`` is defined in the Makefile.

The Python part of the testbench is this file.
"""


async def progress_reporter(tb_hdl):
    """Report progress by printing intermediate counter values."""
    while True:
        # With the following Timer, we sleep exactly the right time
        # to end up printing every 10000th counter value.
        # We could also wake up on each counter value change and
        # print the value if it was modulo 10000,
        # but simulation performance would be much worse.
        await Timer(10000 * 10, "ns")
        tb_hdl._log.info("counter value is %s", tb_hdl.dut_inst.count.value)


@cocotb.test()
async def test_clkgen_hdl(tb_hdl):
    """Run a counter with the clock generator implemented in HDL"""

    tb_hdl.start_high <= 1
    tb_hdl.period_ns <= 10

    cocotb.fork(progress_reporter(tb_hdl))

    # pull the reset
    tb_hdl.dut_inst.rst_n <= 0
    await Timer(5, "ns")
    tb_hdl.dut_inst.rst_n <= 1

    await Timer(MAXCOUNT * 10, "ns")
    act = tb_hdl.dut_inst.count.value
    exp = MAXCOUNT
    assert act == exp, "actual={}, expected={}".format(act, exp)


@cocotb.test()
async def test_clkgen_python(tb_hdl):
    """Run a counter with the clock generator implemented in Python"""

    # Inject the clock at the DUT instance.
    # The HDL clkgen module is still present but unused.
    clock = Clock(tb_hdl.dut_inst.clk, 10, units="ns")
    cocotb.fork(clock.start(start_high=True))

    cocotb.fork(progress_reporter(tb_hdl))

    # pull the reset
    tb_hdl.dut_inst.rst_n <= 0
    await Timer(5, "ns")
    tb_hdl.dut_inst.rst_n <= 1

    await Timer(MAXCOUNT * 10, "ns")
    act = tb_hdl.dut_inst.count.value
    exp = MAXCOUNT
    assert act == exp, "actual={}, expected={}".format(act, exp)
