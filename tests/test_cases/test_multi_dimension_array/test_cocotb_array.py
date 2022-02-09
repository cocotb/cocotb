import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_in_vect_packed(dut):
    test_value = 0x5
    dut.in_vect_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_packed.value == test_value


@cocotb.test()
async def test_in_vect_unpacked(dut):
    test_value = [0x1, 0x0, 0x1]
    dut.in_vect_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_unpacked.value == test_value


@cocotb.test()
async def test_in_arr(dut):
    test_value = 0x5
    dut.in_arr.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr.value == test_value


@cocotb.test()
async def test_in_2d_vect_packed_packed(dut):
    test_value = (0x5 << 6) | (0x5 << 3) | 0x5
    dut.in_2d_vect_packed_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_vect_packed_packed.value == test_value


@cocotb.test()
async def test_in_2d_vect_packed_unpacked(dut):
    test_value = [0x5, 0x5, 0x5]
    dut.in_2d_vect_packed_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_vect_packed_unpacked.value == test_value


@cocotb.test()
async def test_in_2d_vect_unpacked_unpacked(dut):
    test_value = 3 * [[0x1, 0x0, 0x1]]
    dut.in_2d_vect_unpacked_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_vect_unpacked_unpacked.value == test_value


@cocotb.test()
async def test_in_arr_packed(dut):
    test_value = 365
    dut.in_arr_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_packed.value == test_value


@cocotb.test()
async def test_in_arr_unpacked(dut):
    test_value = [0x5, 0x5, 0x5]
    dut.in_arr_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_unpacked.value == test_value


@cocotb.test()
async def test_in_2d_arr(dut):
    test_value = 365
    dut.in_2d_arr.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_arr.value == test_value


@cocotb.test()
async def test_in_vect_packed_packed_packed(dut):
    test_value = 95869805
    dut.in_vect_packed_packed_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_packed_packed_packed.value == test_value


# Questa is unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
@cocotb.test(
    expect_error=IndexError
    if cocotb.LANGUAGE == "verilog" and cocotb.SIM_NAME.lower().startswith("modelsim")
    else ()
)
async def test_in_vect_packed_packed_unpacked(dut):
    test_value = [365, 365, 365]
    dut.in_vect_packed_packed_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_packed_packed_unpacked.value == test_value


@cocotb.test()
async def test_in_vect_packed_unpacked_unpacked(dut):
    test_value = 3 * [3 * [5]]
    dut.in_vect_packed_unpacked_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_packed_unpacked_unpacked.value == test_value


@cocotb.test()
async def test_in_vect_unpacked_unpacked_unpacked(dut):
    test_value = 3 * [3 * [[1, 0, 1]]]
    dut.in_vect_unpacked_unpacked_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_unpacked_unpacked_unpacked.value == test_value


@cocotb.test()
async def test_in_arr_packed_packed(dut):
    test_value = (365 << 18) | (365 << 9) | (365)
    dut.in_arr_packed_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_packed_packed.value == test_value


# Questa is unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
@cocotb.test(
    expect_error=IndexError
    if cocotb.LANGUAGE == "verilog" and cocotb.SIM_NAME.lower().startswith("modelsim")
    else ()
)
async def test_in_arr_packed_unpacked(dut):
    test_value = [365, 365, 365]
    dut.in_arr_packed_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_packed_unpacked.value == test_value


@cocotb.test()
async def test_in_arr_unpacked_unpacked(dut):
    test_value = 3 * [3 * [5]]
    dut.in_arr_unpacked_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_unpacked_unpacked.value == test_value


@cocotb.test()
async def test_in_2d_arr_packed(dut):
    test_value = (365 << 18) | (365 << 9) | (365)
    dut.in_2d_arr_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_arr_packed.value == test_value


# Questa is unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
@cocotb.test(
    expect_error=IndexError
    if cocotb.LANGUAGE == "verilog" and cocotb.SIM_NAME.lower().startswith("modelsim")
    else ()
)
async def test_in_2d_arr_unpacked(dut):
    test_value = [365, 365, 365]
    dut.in_2d_arr_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_arr_unpacked.value == test_value


@cocotb.test()
async def test_in_3d_arr(dut):
    test_value = (365 << 18) | (365 << 9) | (365)
    dut.in_3d_arr.value = test_value
    await Timer(1, "ns")
    assert dut.out_3d_arr.value == test_value
