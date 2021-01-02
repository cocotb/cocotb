# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for handles
"""
import logging
import random
import cocotb
from cocotb.triggers import Timer

from common import assert_raises


@cocotb.test()
async def test_lessthan_raises_error(dut):
    """
    Test that trying to use <= as if it were a comparison produces an error
    """
    ret = dut.stream_in_data <= 0x12
    try:
        bool(ret)
    except TypeError:
        pass
    else:
        assert False, "No exception was raised when confusing comparison with assignment"


@cocotb.test()
async def test_bad_attr(dut):

    with assert_raises(AttributeError):
        fake_signal = dut.fake_signal

    try:
        _ = dut.stream_in_data.whoops
    except AttributeError as e:
        assert 'whoops' in str(e)
    else:
        assert False, "Expected AttributeError"


# strings are not supported on Icarus
@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith("icarus"))
async def test_string_handle_takes_bytes(dut):
    dut.stream_in_string.value = b"bytes"
    await cocotb.triggers.Timer(10, 'ns')
    val = dut.stream_in_string.value
    assert isinstance(val, bytes)
    assert val == b"bytes"


async def test_delayed_assignment_still_errors(dut):
    """ Writing a bad value should fail even if the write is scheduled to happen later """

    # note: all these fail because BinaryValue.assign rejects them

    with assert_raises(ValueError):
        dut.stream_in_int.setimmediatevalue("1010 not a real binary string")
    with assert_raises(TypeError):
        dut.stream_in_int.setimmediatevalue([])

    with assert_raises(ValueError):
        dut.stream_in_int <= "1010 not a real binary string"
    with assert_raises(TypeError):
        dut.stream_in_int <= []


async def int_values_test(signal, values):
    """Test integer access to a signal."""

    log = logging.getLogger("cocotb.test")
    for val in values:
        signal <= val
        await Timer(10, 'ns')

        if val < 0:
            got = signal.value.signed_integer
        else:
            got = int(signal)

        if got != val:
            log.error("Expected value %d, got value %d" %(val, got))
        assert got == val


def gen_int_test_values(n_bits):
    """Generates a list of int test values for a given number of bits."""
    unsigned_min = 0
    unsigned_max = 2**n_bits-1
    signed_min = -2**(n_bits-1)
    signed_max = 2**(n_bits-1)-1

    return [1, -1, 4, -4, unsigned_min, unsigned_max, signed_min, signed_max]


def gen_int_ovfl_value(n_bits):
    return 2**n_bits


def gen_int_unfl_value(n_bits):
    return -2**(n_bits-1)-1


@cocotb.test()
async def test_int_8bit(dut):
    """Test int access to 8-bit vector."""
    values = gen_int_test_values(len(dut.stream_in_data))
    await int_values_test(dut.stream_in_data, values)


@cocotb.test(expect_error=OverflowError)
async def test_int_8bit_overflow(dut):
    """Test 8-bit vector overflow."""
    value = gen_int_ovfl_value(len(dut.stream_in_data))
    await int_values_test(dut.stream_in_data, [value])


@cocotb.test(expect_error=OverflowError)
async def test_int_8bit_underflow(dut):
    """Test 8-bit vector underflow."""
    value = gen_int_unfl_value(len(dut.stream_in_data))
    await int_values_test(dut.stream_in_data, [value])


@cocotb.test()
async def test_int_32bit(dut):
    """Test int access to 32-bit vector."""
    values = gen_int_test_values(len(dut.stream_in_data_dword))
    await int_values_test(dut.stream_in_data_dword, values)


@cocotb.test(expect_error=OverflowError)
async def test_int_32bit_overflow(dut):
    """Test 32-bit vector overflow."""
    value = gen_int_ovfl_value(len(dut.stream_in_data_dword))
    await int_values_test(dut.stream_in_data_dword, [value])


@cocotb.test(expect_error=OverflowError)
async def test_int_32bit_underflow(dut):
    """Test 32-bit vector underflow."""
    value = gen_int_unfl_value(len(dut.stream_in_data_dword))
    await int_values_test(dut.stream_in_data_dword, [value])


@cocotb.test()
async def test_int_39bit(dut):
    """Test int access to 39-bit vector."""
    values = gen_int_test_values(len(dut.stream_in_data_39bit))
    await int_values_test(dut.stream_in_data_39bit, values)


@cocotb.test(expect_error=OverflowError)
async def test_int_39bit_overflow(dut):
    """Test 39-bit vector overflow."""
    value = gen_int_ovfl_value(len(dut.stream_in_data_39bit))
    await int_values_test(dut.stream_in_data_39bit, [value])


@cocotb.test(expect_error=OverflowError)
async def test_int_39bit_underflow(dut):
    """Test 39-bit vector underflow."""
    value = gen_int_unfl_value(len(dut.stream_in_data_39bit))
    await int_values_test(dut.stream_in_data_39bit, [value])


@cocotb.test()
async def test_int_64bit(dut):
    """Test int access to 64-bit vector."""
    values = gen_int_test_values(len(dut.stream_in_data_wide))
    await int_values_test(dut.stream_in_data_wide, values)


@cocotb.test(expect_error=OverflowError)
async def test_int_64bit_overflow(dut):
    """Test 64-bit vector overflow."""
    value = gen_int_ovfl_value(len(dut.stream_in_data_wide))
    await int_values_test(dut.stream_in_data_wide, [value])


@cocotb.test(expect_error=OverflowError)
async def test_int_64bit_underflow(dut):
    """Test 64-bit vector underflow."""
    value = gen_int_unfl_value(len(dut.stream_in_data_wide))
    await int_values_test(dut.stream_in_data_wide, [value])


@cocotb.test()
async def test_int_128bit(dut):
    """Test int access to 128-bit vector."""
    values = gen_int_test_values(len(dut.stream_in_data_dqword))
    await int_values_test(dut.stream_in_data_dqword, values)


@cocotb.test(expect_error=OverflowError)
async def test_int_128bit_overflow(dut):
    """Test 128-bit vector overflow."""
    value = gen_int_ovfl_value(len(dut.stream_in_data_dqword))
    await int_values_test(dut.stream_in_data_dqword, [value])


@cocotb.test(expect_error=OverflowError)
async def test_int_128bit_underflow(dut):
    """Test 128-bit vector underflow."""
    value = gen_int_unfl_value(len(dut.stream_in_data_dqword))
    await int_values_test(dut.stream_in_data_dqword, [value])


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME in ["Icarus Verilog"] else ())
async def test_integer(dut):
    """Test access to integers."""
    for value in [0, 1, -1, 4, -4, 2**31-1, -2**31]:
        dut.stream_in_int = value
        await cocotb.triggers.Timer(10, 'ns')
        assert int(dut.stream_in_int) == value


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME in ["Icarus Verilog"] else OverflowError)
async def test_integer_overflow(dut):
    """Test integer overflow."""
    value = 2**31
    dut.stream_in_int = value
    await cocotb.triggers.Timer(10, 'ns')
    assert int(dut.stream_in_int) == value


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME in ["Icarus Verilog"] else OverflowError)
async def test_integer_underflow(dut):
    """Test integer underflow."""
    value = -2**32-1
    dut.stream_in_int = value
    await cocotb.triggers.Timer(10, 'ns')
    assert int(dut.stream_in_int) == value


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME in ["Icarus Verilog"] else ())
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
    dut.stream_in_real = val
    await timer_shortest
    await timer_shortest  # FIXME: Workaround for VHPI scheduling - needs investigation
    got = float(dut.stream_out_real)
    log.info("Read back value %g" % got)
    assert got == val, "Values didn't match!"


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME in ["Icarus Verilog"] else ())
async def test_real_assign_int(dut):
    """Assign a random integer value to ensure we can write types convertible to
    int, read it back from the DUT and check it matches what we assigned.
    """
    val = random.randint(-2**31, 2**31 - 1)
    log = logging.getLogger("cocotb.test")
    timer_shortest = Timer(1, "step")
    await timer_shortest
    log.info("Setting the value %i" % val)
    dut.stream_in_real <= val
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
    dut._id("_underscore_name", extended=False) <= 0
    await Timer(1, 'ns')
    assert dut._id("_underscore_name", extended=False).value == 0
    dut._id("_underscore_name", extended=False) <= 1
    await Timer(1, 'ns')
    assert dut._id("_underscore_name", extended=False).value == 1
    dut._id("_underscore_name", extended=False) <= 0
    await Timer(1, 'ns')
    assert dut._id("_underscore_name", extended=False).value == 0
