import logging

import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestFailure
from cocotb.handle import Force, Release


@cocotb.test(expect_fail=cocotb.SIM_NAME in ["GHDL"])
async def test_force_release(dut):
    """
    Test force and release on simulation handles
    """
    log = logging.getLogger("cocotb.test")
    await Timer(10, "ns")
    dut.stream_in_data <= 4
    dut.stream_out_data_comb <= Force(5)
    await Timer(10, "ns")
    got_in = int(dut.stream_in_data)
    got_out = int(dut.stream_out_data_comb)
    log.info("dut.stream_in_data = %d" % got_in)
    log.info("dut.stream_out_data_comb = %d" % got_out)
    if got_in == got_out:
        raise TestFailure("stream_in_data and stream_out_data_comb should not match when force is active!")

    dut.stream_out_data_comb <= Release()
    dut.stream_in_data <= 3
    await Timer(10, "ns")
    got_in = int(dut.stream_in_data)
    got_out = int(dut.stream_out_data_comb)
    log.info("dut.stream_in_data = %d" % got_in)
    log.info("dut.stream_out_data_comb = %d" % got_out)
    if got_in != got_out:
        raise TestFailure("stream_in_data and stream_out_data_comb should match when output was released!")
