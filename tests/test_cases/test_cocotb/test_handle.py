# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for handles
"""

import logging
import os
import random
import sys
from enum import Enum, auto

import pytest

import cocotb
from cocotb.handle import StringObject, _GPIResolveX, _Limits
from cocotb.result import TestSuccess
from cocotb.triggers import Timer
from cocotb.types import Logic, LogicArray

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test()
async def test_bad_attr(dut):
    with pytest.raises(AttributeError):
        dut.fake_signal

    try:
        _ = dut.stream_in_data.whoops
    except AttributeError as e:
        assert "whoops" in str(e)
    else:
        assert False, "Expected AttributeError"


# iverilog fails to discover string inputs (gh-2585)
# GHDL fails to discover string input properly (gh-2584)
@cocotb.test(
    expect_error=AttributeError if SIM_NAME.startswith("icarus") else (),
    expect_fail=SIM_NAME.startswith("ghdl"),
)
async def test_string_handle_takes_bytes(dut):
    assert isinstance(dut.stream_in_string, StringObject)
    dut.stream_in_string.value = b"bytes"
    await cocotb.triggers.Timer(10, "ns")
    val = dut.stream_in_string.value
    assert isinstance(val, bytes)
    assert val == b"bytes"


# iverilog fails to discover string inputs (gh-2585)
# GHDL fails to discover string input properly (gh-2584)
@cocotb.test(
    expect_error=AttributeError if SIM_NAME.startswith("icarus") else (),
    expect_fail=SIM_NAME.startswith("ghdl"),
    skip=LANGUAGE in ["verilog"] and SIM_NAME.startswith("riviera"),
)
async def test_string_ansi_color(dut):
    """Check how different simulators treat ANSI-colored strings, see gh-2328"""
    assert isinstance(dut.stream_in_string, StringObject)
    teststr = "\x1b[33myellow\x1b[49m\x1b[39m"
    asciival_sum = sum(ord(char) for char in teststr)
    await cocotb.triggers.Timer(10, "ns")
    dut.stream_in_string.value = bytes(teststr.encode("ascii"))
    await cocotb.triggers.Timer(10, "ns")
    val = dut.stream_in_string.value
    assert isinstance(val, bytes)
    if LANGUAGE in ["vhdl"] and SIM_NAME.startswith("riviera"):
        # Riviera-PRO doesn't return anything with VHDL:
        assert val == b""
        # ...and the value shows up differently in the HDL:
        assert dut.stream_in_string_asciival_sum.value == sum(
            ord(char) for char in teststr.replace("\x1b", "\0")
        )
    elif LANGUAGE in ["verilog"] and SIM_NAME.startswith(("ncsim", "xmsim")):
        # Xcelium with VPI strips the escape char when reading:
        assert val == bytes(teststr.replace("\x1b", "").encode("ascii"))
        # the HDL gets the correct value though:
        assert dut.stream_in_string_asciival_sum.value == asciival_sum
    else:
        assert val == bytes(teststr.encode("ascii"))
        assert dut.stream_in_string_asciival_sum.value == asciival_sum


async def test_delayed_assignment_still_errors(dut):
    """Writing a bad value should fail even if the write is scheduled to happen later"""

    with pytest.raises(ValueError):
        dut.stream_in_int.setimmediatevalue("1010 not a real binary string")
    with pytest.raises(TypeError):
        dut.stream_in_int.setimmediatevalue([])

    with pytest.raises(ValueError):
        dut.stream_in_int.value = "1010 not a real binary string"
    with pytest.raises(TypeError):
        dut.stream_in_int.value = []


async def int_values_test(
    signal, n_bits, limits=_Limits.VECTOR_NBIT, from_bytes=False, to_bytes=False
):
    """Test integer access to a signal."""
    if (from_bytes or to_bytes) and SIM_NAME.startswith("ghdl"):
        raise TestSuccess("ghdl appears to have problems with vpiVectorValue")
    values = gen_int_test_values(n_bits, limits)
    for val in values:
        negative = val < 0
        if from_bytes:
            num_bytes = (n_bits + 7) // 8
            bytes_val = val.to_bytes(
                length=num_bytes, byteorder=sys.byteorder, signed=negative
            )
            signal.value = bytes_val
        else:
            signal.value = val
        await Timer(1, "ns")

        if to_bytes:
            bytes_val = signal.value_as_bytes()
            msb = bytes_val[-1 if sys.byteorder == "little" else 0]
            if negative and n_bits % 8 != 0 and msb >> (n_bits % 8 - 1):
                msb_extended = msb | (0xFF << (n_bits % 8)) & 0xFF
                new_msb = msb_extended.to_bytes(length=1, byteorder=sys.byteorder)
                if sys.byteorder == "little":
                    bytes_val = bytes_val[:-1] + new_msb
                else:
                    bytes_val = new_msb + bytes_val[1:]
            got = int.from_bytes(bytes_val, byteorder=sys.byteorder, signed=negative)
        elif limits == _Limits.VECTOR_NBIT:
            if negative:
                got = signal.value.to_signed()
            else:
                got = signal.value.to_unsigned()
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

    with pytest.raises(OverflowError):
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


signals = [
    "stream_in_data",
    "stream_in_data_dqword",
    "stream_in_data_39bit",
    "stream_in_data_wide",
    "stream_in_data_dqword",
]


class IntTest(Enum):
    INT = auto()
    FROM_BYTES = auto()
    TO_BYTES = auto()


@cocotb.test
@cocotb.parameterize(
    signal=signals,
    test=list(IntTest),
)
async def test_int(dut, signal, test):
    """Test int access to bit vector."""
    handle = getattr(dut, signal)
    await int_values_test(
        handle,
        len(handle),
        from_bytes=(test == IntTest.FROM_BYTES),
        to_bytes=(test == IntTest.TO_BYTES),
    )


@cocotb.test()
@cocotb.parameterize(signal=signals, test=["ovfl", "unfl"])
async def test_int_8bit_overflow(dut, signal, test):
    """Test bit vector overflow / underflow."""
    handle = getattr(dut, signal)
    await int_overflow_test(handle, len(handle), test)


@cocotb.test
@cocotb.parameterize(signal=signals, too_big=[True, False])
async def test_bytes_bad_size(dut, signal, too_big):
    """Test incorrect buffer sizes when setting via bytes."""
    handle = getattr(dut, signal)
    n_bytes = (len(handle) + 7) // 8
    buffer = bytes(n_bytes + (1 if too_big else -1))

    with pytest.raises(ValueError):
        handle.value = buffer


# verilator does not support 4-state signals
# ghdl appears to have problems with vpiVectorVal
@cocotb.test(skip=SIM_NAME.startswith(("verilator", "ghdl")))
@cocotb.parameterize(
    signal=signals,
    resolve_x=list(_GPIResolveX),
)
async def test_bytes_resolve_x(dut, signal, resolve_x):
    """Test resolving non 0 / 1 values when getting bytes."""
    handle = getattr(dut, signal)
    n_bits = len(handle)
    xs = LogicArray("x" * n_bits)
    handle.value = xs
    await Timer(1, "ns")

    if resolve_x == _GPIResolveX.ERROR:
        with pytest.raises(ValueError):
            handle.value_as_bytes(resolve_x)
    else:
        bytes_value = handle.value_as_bytes(resolve_x)
        bytes_int = int.from_bytes(bytes_value, byteorder=sys.byteorder)
        if resolve_x == _GPIResolveX.ZEROS:
            assert bytes_int == 0
        elif resolve_x == _GPIResolveX.ONES:
            assert bytes_int == 2**n_bits - 1
        elif resolve_x == _GPIResolveX.RANDOM:
            assert bytes_value != handle.value_as_bytes(resolve_x)
        else:
            raise RuntimeError(f"Test needs to support resolve_x={resolve_x}")


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
async def test_integer(dut):
    """Test access to integers."""
    if (
        LANGUAGE in ["verilog"]
        and SIM_NAME.startswith("riviera")
        or SIM_NAME.startswith("ghdl")
        or SIM_NAME.startswith("verilator")
    ):
        limits = (
            _Limits.VECTOR_NBIT
        )  # stream_in_int is LogicObject in Riviera and GHDL, not IntegerObject
    else:
        limits = _Limits.SIGNED_NBIT

    await int_values_test(dut.stream_in_int, 32, limits)


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
async def test_integer_overflow(dut):
    """Test integer overflow."""
    if (
        LANGUAGE in ["verilog"]
        and SIM_NAME.startswith("riviera")
        or SIM_NAME.startswith("ghdl")
        or SIM_NAME.startswith("verilator")
    ):
        limits = (
            _Limits.VECTOR_NBIT
        )  # stream_in_int is LogicObject in Riviera and GHDL, not IntegerObject
    else:
        limits = _Limits.SIGNED_NBIT

    await int_overflow_test(dut.stream_in_int, 32, "ovfl", limits)


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
async def test_integer_underflow(dut):
    """Test integer underflow."""
    if (
        LANGUAGE in ["verilog"]
        and SIM_NAME.startswith("riviera")
        or SIM_NAME.startswith("ghdl")
    ):
        limits = (
            _Limits.VECTOR_NBIT
        )  # stream_in_int is LogicObject in Riviera and GHDL, not IntegerObject
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
    log.info(f"Setting the value {val:g}")
    dut.stream_in_real.value = val
    await timer_shortest
    await timer_shortest  # FIXME: Workaround for VHPI scheduling - needs investigation
    got = dut.stream_out_real.value
    log.info(f"Read back value {got:g}")
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
    got = dut.stream_out_real.value
    log.info("Read back value %d" % got)
    assert got == val, "Values didn't match!"


# identifiers starting with `_` are illegal in VHDL
@cocotb.test(skip=LANGUAGE in ("vhdl"))
async def test_access_underscore_name(dut):
    """Test accessing HDL name starting with an underscore"""
    # direct access does not work because we consider such names cocotb-internal
    with pytest.raises(AttributeError):
        dut._underscore_name

    # indirect access works
    dut["_underscore_name"].value = 0
    await Timer(1, "ns")
    assert dut["_underscore_name"].value == 0
    dut["_underscore_name"].value = 1
    await Timer(1, "ns")
    assert dut["_underscore_name"].value == 1
    dut["_underscore_name"].value = 0
    await Timer(1, "ns")
    assert dut["_underscore_name"].value == 0


@cocotb.test()
async def test_assign_LogicArray(dut):
    value = LogicArray(dut.stream_in_data.value)
    value &= LogicArray("0x1X011z")
    dut.stream_in_data.value = value
    with pytest.raises(ValueError):
        dut.stream_in_data.value = LogicArray("010")  # not the correct size


# verilator does not support 4-state signals
# see https://veripool.org/guide/latest/languages.html#unknown-states
@cocotb.test(expect_error=AssertionError if SIM_NAME.startswith("verilator") else ())
async def test_assign_Logic(dut):
    dut.stream_in_ready.value = Logic("X")
    await Timer(1, "ns")
    assert dut.stream_in_ready.value == "x"
    with pytest.raises(ValueError):
        dut.stream_in_data.value = Logic("U")  # not the correct size
