import cocotb
from cocotb.result import TestFailure
from cocotb.triggers import Timer


@cocotb.test()
async def test_in_vect_packed(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_vect_packed type %s" % type(dut.in_vect_packed))
    dut.in_vect_packed = 0x5
    await Timer(1, "ns")
    print("Getting: dut.out_vect_packed type %s" % type(dut.out_vect_packed))
    if dut.out_vect_packed != 0x5:
        raise TestFailure("Failed to readback dut.out_vect_packed")


@cocotb.test()
async def test_in_vect_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_vect_unpacked type %s" % type(dut.in_vect_unpacked))
    dut.in_vect_unpacked = [0x1, 0x0, 0x1]
    await Timer(1, "ns")
    print("Getting: dut.out_vect_unpacked type %s" % type(dut.out_vect_unpacked))
    if dut.out_vect_unpacked != [0x1, 0x0, 0x1]:
        raise TestFailure("Failed to readback dut.out_vect_unpacked")


@cocotb.test()
async def test_in_arr(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_arr type %s" % type(dut.in_arr))
    dut.in_arr = 0x5
    await Timer(1, "ns")
    print("Getting: dut.out_arr type %s" % type(dut.out_arr))
    if dut.out_arr != 0x5:
        raise TestFailure("Failed to readback dut.out_arr")


@cocotb.test()
async def test_in_2d_vect_packed_packed(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_2d_vect_packed_packed type %s" % type(dut.in_2d_vect_packed_packed))
    dut.in_2d_vect_packed_packed = (0x5 << 6) | (0x5 << 3) | 0x5
    await Timer(1, "ns")
    print("Getting: dut.out_2d_vect_packed_packed type %s" % type(dut.out_2d_vect_packed_packed))
    if dut.out_2d_vect_packed_packed != (0x5 << 6) | (0x5 << 3) | 0x5:
        raise TestFailure("Failed to readback dut.out_2d_vect_packed_packed")


@cocotb.test()
async def test_in_2d_vect_packed_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_2d_vect_packed_unpacked type %s" % type(dut.in_2d_vect_packed_unpacked))
    dut.in_2d_vect_packed_unpacked = [0x5, 0x5, 0x5]
    await Timer(1, "ns")
    print("Getting: dut.out_2d_vect_packed_unpacked type %s" % type(dut.out_2d_vect_packed_unpacked))
    if dut.out_2d_vect_packed_unpacked != [0x5, 0x5, 0x5]:
        raise TestFailure("Failed to readback dut.out_2d_vect_packed_unpacked")


@cocotb.test()
async def test_in_2d_vect_unpacked_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_2d_vect_unpacked_unpacked type %s" % type(dut.in_2d_vect_unpacked_unpacked))
    dut.in_2d_vect_unpacked_unpacked = 3*[[0x1, 0x0, 0x1]]
    await Timer(1, "ns")
    print("Getting: dut.out_2d_vect_unpacked_unpacked type %s" % type(dut.out_2d_vect_unpacked_unpacked))
    if dut.out_2d_vect_unpacked_unpacked != 3*[[0x1, 0x0, 0x1]]:
        raise TestFailure("Failed to readback dut.out_2d_vect_unpacked_unpacked")


@cocotb.test()
async def test_in_arr_packed(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_arr_packed type %s" % type(dut.in_arr_packed))
    dut.in_arr_packed = 365
    await Timer(1, "ns")
    print("Getting: dut.out_arr_packed type %s" % type(dut.out_arr_packed))
    if dut.out_arr_packed != 365:
        raise TestFailure("Failed to readback dut.out_arr_packed")


@cocotb.test()
async def test_in_arr_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_arr_unpackedtype %s" % type(dut.in_arr_unpacked))
    dut.in_arr_unpacked = [0x5, 0x5, 0x5]
    await Timer(1, "ns")
    print("Getting: dut.out_arr_unpackedtype %s" % type(dut.out_arr_unpacked))
    if dut.out_arr_unpacked != [0x5, 0x5, 0x5]:
        raise TestFailure("Failed to readback dut.out_arr_unpacked")


@cocotb.test()
async def test_in_2d_arr(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_2d_arr type %s" % type(dut.in_2d_arr))
    dut.in_2d_arr = 365
    await Timer(1, "ns")
    print("Getting: dut.out_2d_arr type %s" % type(dut.out_2d_arr))
    if dut.out_2d_arr != 365:
        raise TestFailure("Failed to readback dut.out_2d_arr")


@cocotb.test()
async def test_in_vect_packed_packed_packed(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_vect_packed_packed_packed type %s" % type(dut.in_vect_packed_packed_packed))
    dut.in_vect_packed_packed_packed = 95869805
    await Timer(1, "ns")
    print("Getting: dut.out_vect_packed_packed_packed type %s" % type(dut.out_vect_packed_packed_packed))
    if dut.out_vect_packed_packed_packed != 95869805:
        raise TestFailure("Failed to readback dut.out_vect_packed_packed_packed")


# Questa unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
@cocotb.test(
    expect_error=IndexError
    if cocotb.LANGUAGE == "verilog" and cocotb.SIM_NAME.lower().startswith("modelsim")
    else ()
)
async def test_in_vect_packed_packed_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_vect_packed_packed_unpacked type %s" % type(dut.in_vect_packed_packed_unpacked))
    dut.in_vect_packed_packed_unpacked = [365, 365, 365]
    await Timer(1, "ns")
    print("Getting: dut.out_vect_packed_packed_unpacked type %s" % type(dut.out_vect_packed_packed_unpacked))
    if dut.out_vect_packed_packed_unpacked != [365, 365, 365]:
        raise TestFailure("Failed to readback dut.out_vect_packed_packed_unpacked")


@cocotb.test()
async def test_in_vect_packed_unpacked_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_vect_packed_unpacked_unpacked type %s" % type(dut.in_vect_packed_unpacked_unpacked))
    dut.in_vect_packed_unpacked_unpacked = 3 *[3 * [5] ]
    await Timer(1, "ns")
    print("Getting: dut.out_vect_packed_unpacked_unpacked type %s" % type(dut.out_vect_packed_unpacked_unpacked))
    if dut.out_vect_packed_unpacked_unpacked != 3 *[3 * [5] ]:
        raise TestFailure("Failed to readback dut.out_vect_packed_unpacked_unpacked")


@cocotb.test()
async def test_in_vect_unpacked_unpacked_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_vect_unpacked_unpacked_unpacked type %s" % type(dut.in_vect_unpacked_unpacked_unpacked))
    dut.in_vect_unpacked_unpacked_unpacked = 3 *[3 * [[1, 0, 1]]]
    await Timer(1, "ns")
    print("Getting: dut.out_vect_unpacked_unpacked_unpacked type %s" % type(dut.out_vect_unpacked_unpacked_unpacked))
    if dut.out_vect_unpacked_unpacked_unpacked != 3 *[3 * [[1, 0, 1]]]:
        raise TestFailure("Failed to readback dut.out_vect_unpacked_unpacked_unpacked")


@cocotb.test()
async def test_in_arr_packed_packed(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_arr_packed_packed type %s" % type(dut.in_arr_packed_packed))
    dut.in_arr_packed_packed = (365 << 18) | (365 << 9) | (365)
    await Timer(1, "ns")
    print("Getting: dut.out_arr_packed_packed type %s" % type(dut.out_arr_packed_packed))
    if dut.out_arr_packed_packed != (365 << 18) | (365 << 9) | (365):
        raise TestFailure("Failed to readback dut.out_arr_packed_packed")


# Questa unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
@cocotb.test(
    expect_error=IndexError
    if cocotb.LANGUAGE == "verilog" and cocotb.SIM_NAME.lower().startswith("modelsim")
    else ()
)
async def test_in_arr_packed_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_arr_packed_unpacked type %s" % type(dut.in_arr_packed_unpacked))
    dut.in_arr_packed_unpacked = [365, 365, 365]
    await Timer(1, "ns")
    print("Getting: dut.out_arr_packed_unpacked type %s" % type(dut.out_arr_packed_unpacked))
    if dut.out_arr_packed_unpacked != [365, 365, 365]:
        raise TestFailure("Failed to readback dut.out_arr_packed_unpacked")


@cocotb.test()
async def test_in_arr_unpacked_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_arr_unpacked_unpacked type %s" % type(dut.in_arr_unpacked_unpacked))
    dut.in_arr_unpacked_unpacked = 3 *[3 * [5] ]
    await Timer(1, "ns")
    print("Getting: dut.out_arr_unpacked_unpacked type %s" % type(dut.out_arr_unpacked_unpacked))
    if dut.out_arr_unpacked_unpacked != 3 *[3 * [5] ]:
        raise TestFailure("Failed to readback dut.out_arr_unpacked_unpacked")


@cocotb.test()
async def test_in_2d_arr_packed(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_2d_arr_packed type %s" % type(dut.in_2d_arr_packed))
    dut.in_2d_arr_packed = (365 << 18) | (365 << 9) | (365)
    await Timer(1, "ns")
    print("Getting: dut.out_2d_arr_packed type %s" % type(dut.out_2d_arr_packed))
    if dut.out_2d_arr_packed != (365 << 18) | (365 << 9) | (365):
        raise TestFailure("Failed to readback dut.out_2d_arr_packed")


# Questa unable to access elements of a logic array if the last dimension is unpacked (gh-2605)
@cocotb.test(
    expect_error=IndexError
    if cocotb.LANGUAGE == "verilog" and cocotb.SIM_NAME.lower().startswith("modelsim")
    else ()
)
async def test_in_2d_arr_unpacked(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_2d_arr_unpacked type %s" % type(dut.in_2d_arr_unpacked))
    dut.in_2d_arr_unpacked = [365, 365, 365]
    await Timer(1, "ns")
    print("Getting: dut.out_2d_arr_unpacked type %s" % type(dut.out_2d_arr_unpacked))
    if dut.out_2d_arr_unpacked != [365, 365, 365]:
        raise TestFailure("Failed to readback dut.out_2d_arr_unpacked")


@cocotb.test()
async def test_in_3d_arr(dut):
    await Timer(1, "ns")
    print("Setting: dut.in_3d_arr type %s" % type(dut.in_3d_arr))
    dut.in_3d_arr = (365 << 18) | (365 << 9) | (365)
    await Timer(1, "ns")
    print("Getting: dut.out_3d_arr type %s" % type(dut.out_3d_arr))
    if dut.out_3d_arr != (365 << 18) | (365 << 9) | (365):
        raise TestFailure("Failed to readback dut.out_3d_arr")
