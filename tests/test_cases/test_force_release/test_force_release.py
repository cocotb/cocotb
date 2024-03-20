import cocotb
from cocotb.handle import Force, Release
from cocotb.triggers import Timer


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith(("ghdl", "verilator")))
async def test_force_release(dut):
    """
    Test force and release on simulation handles
    """
    await Timer(10, "ns")
    dut.stream_in_data.value = 4
    dut.stream_out_data_comb.value = Force(5)
    await Timer(10, "ns")
    assert dut.stream_in_data.value != dut.stream_out_data_comb.value

    dut.stream_out_data_comb.value = Release()
    dut.stream_in_data.value = 3
    await Timer(10, "ns")
    assert dut.stream_in_data.value == dut.stream_out_data_comb.value
