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


@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl")) or
             cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("riviera")))
async def test_string_ansi_color(dut):
    """Check how different simulators treat ANSI-colored strings, see gh-2328"""
    teststr = "\x1b[33myellow\x1b[49m\x1b[39m"
    asciival_sum = sum(ord(char) for char in teststr)
    await cocotb.triggers.Timer(10, 'ns')
    dut.stream_in_string.value = bytes(teststr.encode("ascii"))
    await cocotb.triggers.Timer(10, 'ns')
    val = dut.stream_in_string.value
    assert isinstance(val, bytes)
    if cocotb.LANGUAGE in ["vhdl"] and cocotb.SIM_NAME.lower().startswith("riviera"):
        # Riviera-PRO doesn't return anything with VHDL:
        assert val == b""
        # ...and the value shows up differently in the HDL:
        assert dut.stream_in_string_asciival_sum.value == sum(ord(char) for char in teststr.replace('\x1b', '\0'))
    elif cocotb.LANGUAGE in ["verilog"] and cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim")):
        # Xcelium with VPI strips the escape char when reading:
        assert val == bytes(teststr.replace('\x1b', '').encode("ascii"))
        # the HDL gets the correct value though:
        assert dut.stream_in_string_asciival_sum.value == asciival_sum
    else:
        assert val == bytes(teststr.encode("ascii"))
        assert dut.stream_in_string_asciival_sum.value == asciival_sum


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


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME in ["Icarus Verilog"] else ())
async def test_integer(dut):
    """
    Test access to integers
    """
    log = logging.getLogger("cocotb.test")
    await Timer(10, "ns")
    dut.stream_in_int <= 4
    await Timer(10, "ns")
    await Timer(10, "ns")
    got_in = int(dut.stream_out_int)
    got_out = int(dut.stream_in_int)
    log.info("dut.stream_out_int = %d" % got_out)
    log.info("dut.stream_in_int = %d" % got_in)
    assert got_in == got_out, "stream_in_int and stream_out_int should not match"


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


@cocotb.test()
async def test_reading_writing_logic_array_using_int(dut):
    # in range, < 32 bits, positive
    dut.stream_in_data.value = 1
    await Timer(1, 'ns')
    assert dut.stream_in_data.value.integer == 1
    # in range, < 32 bit, negative
    dut.stream_in_data.value = -1
    await Timer(1, 'ns')
    assert dut.stream_in_data.value.signed_integer == -1
    # in range, >= 32 bit, positive
    dut.stream_in_data_wide.value = 0x1234567890
    await Timer(1, 'ns')
    assert dut.stream_in_data_wide.value.integer == 0x1234567890
    # in range, >= 32 bit, negative
    dut.stream_in_data_wide.value = -0x1234567890
    await Timer(1, 'ns')
    assert dut.stream_in_data_wide.value.signed_integer == -0x1234567890
