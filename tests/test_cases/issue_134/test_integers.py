import logging

import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestFailure


@cocotb.test(expect_error=cocotb.SIM_NAME in ["Icarus Verilog"])
def test_integer(dut):
    """
    Test access to integers
    """
    log = logging.getLogger("cocotb.test")
    yield Timer(10)
    dut.stream_in_int = 4
    yield Timer(10)
    yield Timer(10)
    got_in = int(dut.stream_out_int)
    got_out = int(dut.stream_in_int)
    log.info("dut.stream_out_int = %d" % got_out)
    log.info("dut.stream_in_int = %d" % got_in)
    if got_in != got_out:
        raise TestFailure("stream_in_int and stream_out_int should not match")
