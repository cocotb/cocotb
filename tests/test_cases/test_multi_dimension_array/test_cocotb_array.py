import os

import cocotb
from cocotb.handle import ArrayObject, LogicArrayObject, LogicObject
from cocotb.triggers import Timer

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test()
async def test_in_vect_packed(dut):
    assert isinstance(dut.in_vect_packed, LogicArrayObject)
    assert len(dut.in_vect_packed) == 3

    test_value = 0x5
    dut.in_vect_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_packed.value == test_value


@cocotb.test()
async def test_in_vect_unpacked(dut):
    assert isinstance(dut.in_vect_unpacked, ArrayObject)
    assert len(dut.in_vect_unpacked) == 3

    dut.in_vect_unpacked[0]
    assert isinstance(dut.in_vect_unpacked[0], LogicObject)

    test_value = [0x1, 0x0, 0x1]
    dut.in_vect_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_unpacked.value == test_value


@cocotb.test()
async def test_in_arr(dut):
    assert isinstance(dut.in_arr, LogicArrayObject)
    assert len(dut.in_arr) == 3

    test_value = 0x5
    dut.in_arr.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr.value == test_value


@cocotb.test()
async def test_in_2d_vect_packed_packed(dut):
    assert isinstance(dut.in_2d_vect_packed_packed, LogicArrayObject)
    assert len(dut.in_2d_vect_packed_packed) == 9

    test_value = (0x5 << 6) | (0x5 << 3) | 0x5
    dut.in_2d_vect_packed_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_vect_packed_packed.value == test_value


@cocotb.test()
async def test_in_2d_vect_packed_unpacked(dut):
    assert isinstance(dut.in_2d_vect_packed_unpacked, ArrayObject)
    assert len(dut.in_2d_vect_packed_unpacked) == 3

    dut.in_2d_vect_packed_unpacked[0]
    assert isinstance(dut.in_2d_vect_packed_unpacked[0], LogicArrayObject)
    assert len(dut.in_2d_vect_packed_unpacked[0]) == 3

    test_value = [0x5, 0x5, 0x5]
    dut.in_2d_vect_packed_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_vect_packed_unpacked.value == test_value


# Verilator doesn't support multi-dimensional unpacked arrays (gh-3611)
# Icarus flattens multi-dimensional unpacked arrays (gh-2595)
@cocotb.test(
    expect_fail=SIM_NAME.startswith("icarus"),
)
async def test_in_2d_vect_unpacked_unpacked(dut):
    assert isinstance(dut.in_2d_vect_unpacked_unpacked, ArrayObject)
    assert len(dut.in_2d_vect_unpacked_unpacked) == 3

    dut.in_2d_vect_unpacked_unpacked[0]
    assert isinstance(dut.in_2d_vect_unpacked_unpacked[0], ArrayObject)
    assert len(dut.in_2d_vect_unpacked_unpacked[0]) == 3

    dut.in_2d_vect_unpacked_unpacked[0][0]
    assert isinstance(dut.in_2d_vect_unpacked_unpacked[0][0], LogicObject)

    test_value = 3 * [[0x1, 0x0, 0x1]]
    dut.in_2d_vect_unpacked_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_vect_unpacked_unpacked.value == test_value


@cocotb.test()
async def test_in_arr_packed(dut):
    assert isinstance(dut.in_arr_packed, LogicArrayObject)
    assert len(dut.in_arr_packed) == 9

    test_value = 365
    dut.in_arr_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_packed.value == test_value


@cocotb.test()
async def test_in_arr_unpacked(dut):
    assert isinstance(dut.in_arr_unpacked, ArrayObject)
    assert len(dut.in_arr_unpacked) == 3

    dut.in_arr_unpacked[0]
    assert isinstance(dut.in_arr_unpacked[0], LogicArrayObject)
    assert len(dut.in_arr_unpacked[0]) == 3

    test_value = [0x5, 0x5, 0x5]
    dut.in_arr_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_unpacked.value == test_value


@cocotb.test()
async def test_in_2d_arr(dut):
    assert isinstance(dut.in_2d_arr, LogicArrayObject)
    assert len(dut.in_2d_arr) == 9

    test_value = 365
    dut.in_2d_arr.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_arr.value == test_value


@cocotb.test()
async def test_in_vect_packed_packed_packed(dut):
    assert isinstance(dut.in_vect_packed_packed_packed, LogicArrayObject)
    assert len(dut.in_vect_packed_packed_packed) == 27

    test_value = 95869805
    dut.in_vect_packed_packed_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_packed_packed_packed.value == test_value


# Questa is unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
# Verilator doesn't support multi-dimensional unpacked arrays (gh-3611)
@cocotb.test(
    expect_error=IndexError
    if LANGUAGE == "verilog" and SIM_NAME.startswith("modelsim")
    else ()
)
async def test_in_vect_packed_packed_unpacked(dut):
    assert isinstance(dut.in_vect_packed_packed_unpacked, ArrayObject)
    assert len(dut.in_vect_packed_packed_unpacked) == 3

    dut.in_vect_packed_packed_unpacked[0]
    assert isinstance(dut.in_vect_packed_packed_unpacked[0], LogicArrayObject)
    assert len(dut.in_vect_packed_packed_unpacked[0]) == 9

    test_value = [365, 365, 365]
    dut.in_vect_packed_packed_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_packed_packed_unpacked.value == test_value


# Icarus flattens multi-dimensional unpacked arrays (gh-2595)
@cocotb.test(
    expect_fail=SIM_NAME.startswith("icarus"),
)
async def test_in_vect_packed_unpacked_unpacked(dut):
    assert isinstance(dut.in_vect_packed_unpacked_unpacked, ArrayObject)
    assert len(dut.in_vect_packed_unpacked_unpacked) == 3

    dut.in_vect_packed_unpacked_unpacked[0]
    assert isinstance(dut.in_vect_packed_unpacked_unpacked[0], ArrayObject)
    assert len(dut.in_vect_packed_unpacked_unpacked[0]) == 3

    dut.in_vect_packed_unpacked_unpacked[0][0]
    assert isinstance(dut.in_vect_packed_unpacked_unpacked[0][0], LogicArrayObject)
    assert len(dut.in_vect_packed_unpacked_unpacked[0][0]) == 3

    test_value = 3 * [3 * [5]]
    dut.in_vect_packed_unpacked_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_packed_unpacked_unpacked.value == test_value


# Icarus flattens multi-dimensional unpacked arrays (gh-2595)
@cocotb.test(
    expect_fail=SIM_NAME.startswith("icarus"),
)
async def test_in_vect_unpacked_unpacked_unpacked(dut):
    assert isinstance(dut.in_vect_unpacked_unpacked_unpacked, ArrayObject)
    assert len(dut.in_vect_unpacked_unpacked_unpacked) == 3

    dut.in_vect_unpacked_unpacked_unpacked[0]
    assert isinstance(dut.in_vect_unpacked_unpacked_unpacked[0], ArrayObject)
    assert len(dut.in_vect_unpacked_unpacked_unpacked[0]) == 3

    dut.in_vect_unpacked_unpacked_unpacked[0][0]
    assert isinstance(dut.in_vect_unpacked_unpacked_unpacked[0][0], ArrayObject)
    assert len(dut.in_vect_unpacked_unpacked_unpacked[0][0]) == 3

    dut.in_vect_unpacked_unpacked_unpacked[0][0][0]
    assert isinstance(dut.in_vect_unpacked_unpacked_unpacked[0][0][0], LogicObject)

    test_value = 3 * [3 * [[1, 0, 1]]]
    dut.in_vect_unpacked_unpacked_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_vect_unpacked_unpacked_unpacked.value == test_value


@cocotb.test()
async def test_in_arr_packed_packed(dut):
    assert isinstance(dut.in_arr_packed_packed, LogicArrayObject)
    assert len(dut.in_arr_packed_packed) == 27

    test_value = (365 << 18) | (365 << 9) | (365)
    dut.in_arr_packed_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_packed_packed.value == test_value


# Questa is unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
@cocotb.test(
    expect_error=IndexError
    if LANGUAGE == "verilog" and SIM_NAME.startswith("modelsim")
    else ()
)
async def test_in_arr_packed_unpacked(dut):
    assert isinstance(dut.in_arr_packed_unpacked, ArrayObject)
    assert len(dut.in_arr_packed_unpacked) == 3

    dut.in_arr_packed_unpacked[0]
    assert isinstance(dut.in_arr_packed_unpacked[0], LogicArrayObject)
    assert len(dut.in_arr_packed_unpacked[0]) == 9

    test_value = [365, 365, 365]
    dut.in_arr_packed_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_packed_unpacked.value == test_value


# Icarus flattens multi-dimensional unpacked arrays (gh-2595)
@cocotb.test(
    expect_fail=SIM_NAME.startswith("icarus"),
)
async def test_in_arr_unpacked_unpacked(dut):
    assert isinstance(dut.in_arr_unpacked_unpacked, ArrayObject)
    assert len(dut.in_arr_unpacked_unpacked) == 3

    dut.in_arr_unpacked_unpacked[0]
    assert isinstance(dut.in_arr_unpacked_unpacked[0], ArrayObject)
    assert len(dut.in_arr_unpacked_unpacked[0]) == 3

    dut.in_arr_unpacked_unpacked[0][0]
    assert isinstance(dut.in_arr_unpacked_unpacked[0][0], LogicArrayObject)
    assert len(dut.in_arr_unpacked_unpacked[0][0]) == 3

    test_value = 3 * [3 * [5]]
    dut.in_arr_unpacked_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_arr_unpacked_unpacked.value == test_value


@cocotb.test()
async def test_in_2d_arr_packed(dut):
    assert isinstance(dut.in_2d_arr_packed, LogicArrayObject)
    assert len(dut.in_2d_arr_packed) == 27

    test_value = (365 << 18) | (365 << 9) | (365)
    dut.in_2d_arr_packed.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_arr_packed.value == test_value


# Questa is unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
@cocotb.test(
    expect_error=IndexError
    if LANGUAGE == "verilog" and SIM_NAME.startswith("modelsim")
    else ()
)
async def test_in_2d_arr_unpacked(dut):
    assert isinstance(dut.in_2d_arr_unpacked, ArrayObject)
    assert len(dut.in_2d_arr_unpacked) == 3

    dut.in_2d_arr_unpacked[0]
    assert isinstance(dut.in_2d_arr_unpacked[0], LogicArrayObject)
    assert len(dut.in_2d_arr_unpacked[0]) == 9

    test_value = [365, 365, 365]
    dut.in_2d_arr_unpacked.value = test_value
    await Timer(1, "ns")
    assert dut.out_2d_arr_unpacked.value == test_value


@cocotb.test()
async def test_in_3d_arr(dut):
    assert isinstance(dut.in_3d_arr, LogicArrayObject)
    assert len(dut.in_3d_arr) == 27

    test_value = (365 << 18) | (365 << 9) | (365)
    dut.in_3d_arr.value = test_value
    await Timer(1, "ns")
    assert dut.out_3d_arr.value == test_value
