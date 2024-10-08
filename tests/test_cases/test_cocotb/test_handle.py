# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for handles
"""

import logging
import os
import random

import pytest

import cocotb
from cocotb.handle import LogicObject, StringObject, _Limits
from cocotb.triggers import Edge, FallingEdge, Timer
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


signal_widths = {
    len(sig): sig
    for sig in (
        cocotb.top.stream_in_data,
        cocotb.top.stream_in_data_dword,
        cocotb.top.stream_in_data_39bit,
        cocotb.top.stream_in_data_wide,
        cocotb.top.stream_in_data_dqword,
    )
}


@cocotb.test
@cocotb.parametrize(
    ("width", tuple(signal_widths.keys())),
    ("setimmediate", [True, False]),
)
async def test_int_values(
    _, width: int, setimmediate: bool, limits=_Limits.VECTOR_NBIT
) -> None:
    """Test integer access to a signal."""
    if LANGUAGE == "vhdl" and setimmediate:
        return
    signal = signal_widths[width]
    int_values_test(signal, width, setimmediate, limits)


async def int_values_test(
    signal: LogicObject,
    n_bits: int,
    setimmediate: bool,
    limits: _Limits = _Limits.VECTOR_NBIT,
) -> None:
    """Test integer access to a signal."""
    values = gen_int_test_values(n_bits, limits)
    for val in values:
        if setimmediate:
            signal.setimmediatevalue(val)
        else:
            signal.value = val
        await Timer(1, "ns")

        if limits == _Limits.VECTOR_NBIT:
            if val < 0:
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


@cocotb.test
@cocotb.parametrize(
    ("width", tuple(signal_widths.keys())),
    ("test_mode", ["ovfl", "unfl"]),
    ("setimmediate", [True, False]),
)
async def test_vector_overflow(
    _,
    width: int,
    test_mode: str,
    setimmediate: bool,
    limits=_Limits.VECTOR_NBIT,
) -> None:
    if LANGUAGE == "vhdl" and setimmediate:
        return
    signal = signal_widths[width]
    int_overflow_test(signal, width, test_mode, setimmediate, limits)


async def int_overflow_test(
    signal: LogicObject,
    n_bits: int,
    test_mode: str,
    setimmediate: bool,
    limits: _Limits = _Limits.VECTOR_NBIT,
) -> None:
    """Test integer overflow."""
    if test_mode == "ovfl":
        value = gen_int_ovfl_value(n_bits, limits)
    elif test_mode == "unfl":
        value = gen_int_unfl_value(n_bits, limits)
    else:
        assert False, f"bad test_mode {test_mode}"

    with pytest.raises(OverflowError):
        if setimmediate:
            signal.setimmediatevalue(value)
        else:
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


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
@cocotb.parametrize(("setimmediate", [True, False]))
async def test_integer(dut, setimmediate: bool) -> None:
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

    await int_values_test(dut.stream_in_int, 32, setimmediate, limits)


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
@cocotb.parametrize(("setimmediate", [True, False]))
async def test_integer_overflow(dut, setimmediate: bool) -> None:
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

    await int_overflow_test(dut.stream_in_int, 32, "ovfl", setimmediate, limits)


@cocotb.test(expect_error=AttributeError if SIM_NAME.startswith("icarus") else ())
@cocotb.parametrize(("setimmediate", [True, False]))
async def test_integer_underflow(dut, setimmediate: bool) -> None:
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

    await int_overflow_test(dut.stream_in_int, 32, "unfl", setimmediate, limits)


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


@cocotb.test
async def test_assign_string(dut):
    dut.stream_in_data.value = "10101010"
    await Timer(1, "ns")
    assert dut.stream_in_data.value == "10101010"
    with pytest.raises(OverflowError):
        dut.stream_in_data.value = "XXX"  # not the correct size
    with pytest.raises(ValueError):
        dut.stream_in_data.value = "lol"  # not the correct values
    await Timer(1, "ns")
    assert dut.stream_in_data.value == "10101010"


@cocotb.test(
    skip=LANGUAGE in ["vhdl"],
)
async def test_assign_immediate(dut):
    dut.mybits_uninitialized.setimmediatevalue(2)
    assert dut.mybits_uninitialized.value == 2

    dut.mybits_uninitialized.setimmediatevalue("01")
    assert dut.mybits_uninitialized.value == "01"

    dut.mybits_uninitialized.setimmediatevalue(LogicArray("11"))
    assert dut.mybits_uninitialized.value == LogicArray("11")


@cocotb.test(
    skip=LANGUAGE in ["vhdl"],
)
async def test_immediate_reentrace(dut):
    dut.mybits_uninitialized.value = 0
    await Timer(1, "ns")
    seen = 0

    async def nested_watch():
        await FallingEdge(dut.mybit)
        raise RuntimeError("Should have been cancelled")

    nested = cocotb.start_soon(nested_watch())

    async def watch():
        nonlocal seen, nested
        await Edge(dut.mybits_uninitialized)
        seen += 1
        dut.mybit.setimmediatevalue(0)
        with pytest.warns(FutureWarning):
            nested.cancel()

    cocotb.start_soon(watch())
    await Timer(1, "ns")

    dut.mybits_uninitialized.setimmediatevalue(2)
    await Timer(1, "ns")
    assert seen == 1
