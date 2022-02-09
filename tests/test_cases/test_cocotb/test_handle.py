# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for handles
"""
import logging
import random

from common import assert_raises

import cocotb
from cocotb.handle import _Limits
from cocotb.triggers import Timer
from cocotb.types import LogicArray

SIM_NAME = cocotb.SIM_NAME.lower()


@cocotb.test()
async def test_bad_attr(dut):

    with assert_raises(AttributeError):
        fake_signal = dut.fake_signal

    try:
        _ = dut.stream_in_data.whoops
    except AttributeError as e:
        assert "whoops" in str(e)
    else:
        assert False, "Expected AttributeError"


# iverilog fails to discover string inputs (gh-2585)
# GHDL fails to discover string input properly (gh-2584)
@cocotb.test(
    expect_error=AttributeError
    if SIM_NAME.startswith("icarus")
    else TypeError
    if SIM_NAME.startswith("ghdl")
    else ()
)
async def test_string_handle_takes_bytes(dut):
    dut.stream_in_string.value = b"bytes"
    await cocotb.triggers.Timer(10, "ns")
    val = dut.stream_in_string.value
    assert isinstance(val, bytes)
    assert val == b"bytes"


# iverilog fails to discover string inputs (gh-2585)
# GHDL fails to discover string input properly (gh-2584)
@cocotb.test(
    expect_error=AttributeError
    if SIM_NAME.startswith("icarus")
    else TypeError
    if SIM_NAME.startswith("ghdl")
    else (),
    skip=cocotb.LANGUAGE in ["verilog"] and SIM_NAME.startswith("riviera"),
)
async def test_string_ansi_color(dut):
    """Check how different simulators treat ANSI-colored strings, see gh-2328"""
    teststr = "\x1b[33myellow\x1b[49m\x1b[39m"
    asciival_sum = sum(ord(char) for char in teststr)
    await cocotb.triggers.Timer(10, "ns")
    dut.stream_in_string.value = bytes(teststr.encode("ascii"))
    await cocotb.triggers.Timer(10, "ns")
    val = dut.stream_in_string.value
    assert isinstance(val, bytes)
    if cocotb.LANGUAGE in ["vhdl"] and SIM_NAME.startswith("riviera"):
        # Riviera-PRO doesn't return anything with VHDL:
        assert val == b""
        # ...and the value shows up differently in the HDL:
        assert dut.stream_in_string_asciival_sum.value == sum(
            ord(char) for char in teststr.replace("\x1b", "\0")
        )
    elif cocotb.LANGUAGE in ["verilog"] and SIM_NAME.startswith(("ncsim", "xmsim")):
        # Xcelium with VPI strips the escape char when reading:
        assert val == bytes(teststr.replace("\x1b", "").encode("ascii"))
        # the HDL gets the correct value though:
        assert dut.stream_in_string_asciival_sum.value == asciival_sum
    else:
        assert val == bytes(teststr.encode("ascii"))
        assert dut.stream_in_string_asciival_sum.value == asciival_sum


async def test_delayed_assignment_still_errors(dut):
    """Writing a bad value should fail even if the write is scheduled to happen later"""

    # note: all these fail because BinaryValue.assign rejects them

    with assert_raises(ValueError):
        dut.stream_in_int.setimmediatevalue("1010 not a real binary string")
    with assert_raises(TypeError):
        dut.stream_in_int.setimmediatevalue([])

    with assert_raises(ValueError):
        dut.stream_in_int.value = "1010 not a real binary string"
    with assert_raises(TypeError):
        dut.stream_in_int.value = []


async def int_values_test(signal, n_bits, limits=_Limits.VECTOR_NBIT):
    """Test integer access to a signal."""
    log = logging.getLogger("cocotb.test")
    values = gen_int_test_values(n_bits, limits)
    for val in values:
        signal.value = val
        await Timer(1, "ns")

        if limits == _Limits.VECTOR_NBIT:
            if val < 0:
                got = signal.value.signed_integer
            else:
                got = signal.value.integer
        else:
            got = signal.value

        assert got == val


def gen_int_test_values(n_bits, limits=_Limits.VECTOR_NBIT):
    """Generates a list of int test values for a given number of bits."""
    unsigned_min = 0
    unsigned_max = 2**n_bits - 1
    signed_min = -(2 ** (n_bits - 1))
    signed_max = 2 ** (n_bits - 1) - 1

    if limits == _Limits.VECTOR_NBIT:
        return [1, -1, 4, -4, unsigned_min, unsigned_max, signed_min, signed_max]
    elif limits == _Limits.SIGNED_NBIT:
        return [1, -1, 4, -4, signed_min, signed_max]
    else:
        return [1, -1, 4, -4, unsigned_min, unsigned_max]


async def int_overflow_test(signal, n_bits, test_mode, limits=_Limits.VECTOR_NBIT):
    """Test integer overflow."""
    if test_mode == "ovfl":
        value = gen_int_ovfl_value(n_bits, limits)
    elif test_mode == "unfl":
        value = gen_int_unfl_value(n_bits, limits)
    else:
        value = None

    with assert_raises(OverflowError):
        signal.value = value


def gen_int_ovfl_value(n_bits, limits=_Limits.VECTOR_NBIT):
    unsigned_max = 2**n_bits - 1
    signed_max = 2 ** (n_bits - 1) - 1

    if limits == _Limits.SIGNED_NBIT:
        return signed_max + 1
    elif limits == _Limits.UNSIGNED_NBIT:
        return unsigned_max + 1
    else:
        return unsigned_max + 1


def gen_int_unfl_value(n_bits, limits=_Limits.VECTOR_NBIT):
    unsigned_min = 0
    signed_min = -(2 ** (n_bits - 1))

    if limits == _Limits.SIGNED_NBIT:
        return signed_min - 1
    elif limits == _Limits.UNSIGNED_NBIT:
        return unsigned_min - 1
    else:
        return signed_min - 1


@cocotb.test()
async def test_int_8bit(dut):
    """Test int access to 8-bit vector."""
    await int_values_test(dut.stream_in_data, len(dut.stream_in_data))


@cocotb.test()
async def test_int_8bit_overflow(dut):
    """Test 8-bit vector overflow."""
    await int_overflow_test(dut.stream_in_data, len(dut.stream_in_data), "ovfl")


@cocotb.test()
async def test_int_8bit_underflow(dut):
    """Test 8-bit vector underflow."""
    await int_overflow_test(dut.stream_in_data, len(dut.stream_in_data), "unfl")


@cocotb.test()
async def test_int_32bit(dut):
    """Test int access to 32-bit vector."""
    await int_values_test(dut.stream_in_data_dword, len(dut.stream_in_data_dword))


@cocotb.test()
async def test_int_32bit_overflow(dut):
    """Test 32-bit vector overflow."""
    await int_overflow_test(
        dut.stream_in_data_dword, len(dut.stream_in_data_dword), "ovfl"
    )


@cocotb.test()
async def test_int_32bit_underflow(dut):
    """Test 32-bit vector underflow."""
    await int_overflow_test(
        dut.stream_in_data_dword, len(dut.stream_in_data_dword), "unfl"
    )


@cocotb.test()
async def test_int_39bit(dut):
    """Test int access to 39-bit vector."""
    await int_values_test(dut.stream_in_data_39bit, len(dut.stream_in_data_39bit))


@cocotb.test()
async def test_int_39bit_overflow(dut):
    """Test 39-bit vector overflow."""
    await int_overflow_test(
        dut.stream_in_data_39bit, len(dut.stream_in_data_39bit), "ovfl"
    )


@cocotb.test()
async def test_int_39bit_underflow(dut):
    """Test 39-bit vector underflow."""
    await int_overflow_test(
        dut.stream_in_data_39bit, len(dut.stream_in_data_39bit), "unfl"
    )


@cocotb.test()
async def test_int_64bit(dut):
    """Test int access to 64-bit vector."""
    await int_values_test(dut.stream_in_data_wide, len(dut.stream_in_data_wide))


@cocotb.test()
async def test_int_64bit_overflow(dut):
    """Test 64-bit vector overflow."""
    await int_overflow_test(
        dut.stream_in_data_wide, len(dut.stream_in_data_wide), "ovfl"
    )


@cocotb.test()
async def test_int_64bit_underflow(dut):
    """Test 64-bit vector underflow."""
    await int_overflow_test(
        dut.stream_in_data_wide, len(dut.stream_in_data_wide), "unfl"
    )


@cocotb.test()
async def test_int_128bit(dut):
    """Test int access to 128-bit vector."""
    await int_values_test(dut.stream_in_data_dqword, len(dut.stream_in_data_dqword))


@cocotb.test()
async def test_int_128bit_overflow(dut):
    """Test 128-bit vector overflow."""
    await int_overflow_test(
        dut.stream_in_data_dqword, len(dut.stream_in_data_dqword), "ovfl"
    )


@cocotb.test()
async def test_int_128bit_underflow(dut):
    """Test 128-bit vector underflow."""
    await int_overflow_test(
        dut.stream_in_data_dqword, len(dut.stream_in_data_dqword), "unfl"
    )


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
async def test_integer(dut):
    """Test access to integers."""
    if (
        cocotb.LANGUAGE in ["verilog"]
        and SIM_NAME.startswith("riviera")
        or SIM_NAME.startswith("ghdl")
    ):
        limits = (
            _Limits.VECTOR_NBIT
        )  # stream_in_int is ModifiableObject in Riviera and GHDL, not IntegerObject
    else:
        limits = _Limits.SIGNED_NBIT

    await int_values_test(dut.stream_in_int, 32, limits)


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
async def test_integer_overflow(dut):
    """Test integer overflow."""
    if (
        cocotb.LANGUAGE in ["verilog"]
        and SIM_NAME.startswith("riviera")
        or SIM_NAME.startswith("ghdl")
    ):
        limits = (
            _Limits.VECTOR_NBIT
        )  # stream_in_int is ModifiableObject in Riviera and GHDL, not IntegerObject
    else:
        limits = _Limits.SIGNED_NBIT

    await int_overflow_test(dut.stream_in_int, 32, "ovfl", limits)


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
async def test_integer_underflow(dut):
    """Test integer underflow."""
    if (
        cocotb.LANGUAGE in ["verilog"]
        and SIM_NAME.startswith("riviera")
        or SIM_NAME.startswith("ghdl")
    ):
        limits = (
            _Limits.VECTOR_NBIT
        )  # stream_in_int is ModifiableObject in Riviera and GHDL, not IntegerObject
    else:
        limits = _Limits.SIGNED_NBIT

    await int_overflow_test(dut.stream_in_int, 32, "unfl", limits)


# GHDL unable to find real signals (gh-2589)
# iverilog unable to find real signals (gh-2590)
@cocotb.test(
    expect_error=AttributeError
    if SIM_NAME.startswith("icarus")
    else AttributeError
    if SIM_NAME.startswith("ghdl")
    else ()
)
async def test_real_assign_double(dut):
    """
    Assign a random floating point value, read it back from the DUT and check
    it matches what we assigned
    """
    val = random.uniform(-1e307, 1e307)
    log = logging.getLogger("cocotb.test")
    timer_shortest = Timer(1, "step")
    await timer_shortest
    log.info("Setting the value %g" % val)
    dut.stream_in_real.value = val
    await timer_shortest
    await timer_shortest  # FIXME: Workaround for VHPI scheduling - needs investigation
    got = float(dut.stream_out_real)
    log.info("Read back value %g" % got)
    assert got == val, "Values didn't match!"


# GHDL unable to find real signals (gh-2589)
# iverilog unable to find real signals (gh-2590)
@cocotb.test(
    expect_error=AttributeError
    if SIM_NAME.startswith("icarus")
    else AttributeError
    if SIM_NAME.startswith("ghdl")
    else ()
)
async def test_real_assign_int(dut):
    """Assign a random integer value to ensure we can write types convertible to
    int, read it back from the DUT and check it matches what we assigned.
    """
    val = random.randint(-(2**31), 2**31 - 1)
    log = logging.getLogger("cocotb.test")
    timer_shortest = Timer(1, "step")
    await timer_shortest
    log.info("Setting the value %i" % val)
    dut.stream_in_real.value = val
    await timer_shortest
    await timer_shortest  # FIXME: Workaround for VHPI scheduling - needs investigation
    got = dut.stream_out_real
    log.info("Read back value %d" % got)
    assert got == float(val), "Values didn't match!"


# identifiers starting with `_` are illegal in VHDL
@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def test_access_underscore_name(dut):
    """Test accessing HDL name starting with an underscore"""
    # direct access does not work because we consider such names cocotb-internal
    with assert_raises(AttributeError):
        dut._underscore_name

    # indirect access works
    dut._id("_underscore_name", extended=False).value = 0
    await Timer(1, "ns")
    assert dut._id("_underscore_name", extended=False).value == 0
    dut._id("_underscore_name", extended=False).value = 1
    await Timer(1, "ns")
    assert dut._id("_underscore_name", extended=False).value == 1
    dut._id("_underscore_name", extended=False).value = 0
    await Timer(1, "ns")
    assert dut._id("_underscore_name", extended=False).value == 0


@cocotb.test()
async def assign_LogicArray(dut):
    value = LogicArray(dut.stream_in_data.value)
    value &= LogicArray("0x1X011z")
    dut.stream_in_data.value = value
