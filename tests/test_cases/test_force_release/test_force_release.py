import logging

import cocotb
from cocotb.triggers import Timer
from cocotb.handle import Force, Release


@cocotb.test(
    expect_fail=cocotb.SIM_NAME.lower().startswith("ghdl")
)
async def test_force_release(dut):
    """
    Test force and release on simulation handles
    """
    log = logging.getLogger("cocotb.test")
    await Timer(10, "ns")
    dut.stream_in_data.value = 4
    dut.stream_out_data_comb.value = Force(5)
    await Timer(10, "ns")
    got_in = int(dut.stream_in_data)
    got_out = int(dut.stream_out_data_comb)
    log.info("dut.stream_in_data = %d" % got_in)
    log.info("dut.stream_out_data_comb = %d" % got_out)
    assert got_in != got_out

    dut.stream_out_data_comb.value = Release()
    dut.stream_in_data.value = 3
    await Timer(10, "ns")
    got_in = int(dut.stream_in_data)
    got_out = int(dut.stream_out_data_comb)
    log.info("dut.stream_in_data = %d" % got_in)
    log.info("dut.stream_out_data_comb = %d" % got_out)
    assert got_in == got_out
