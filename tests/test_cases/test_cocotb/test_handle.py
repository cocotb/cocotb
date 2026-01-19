# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for handles
"""

from __future__ import annotations

import logging
import os
import pickle
import random
from typing import Any

import pytest

import cocotb
import cocotb.triggers
from cocotb.handle import Immediate, StringObject
from cocotb.triggers import FallingEdge, Timer, ValueChange
from cocotb.types import Logic, LogicArray
from cocotb_tools.sim_versions import RivieraVersion

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()
SIM_VERSION = cocotb.SIM_VERSION

riviera_before_2025_04 = SIM_NAME.startswith("riviera") and RivieraVersion(
    SIM_VERSION
) < RivieraVersion("2025.04")


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


@cocotb.xfail(
    SIM_NAME.startswith("icarus"),
    raises=AttributeError,
    reason="iverilog fails to discover string inputs (gh-2585)",
)
@cocotb.xfail(
    SIM_NAME.startswith("ghdl"),
    reason="GHDL fails to discover string input properly (gh-2584)",
)
@cocotb.test
async def test_string_handle_takes_bytes(dut):
    assert isinstance(dut.stream_in_string, StringObject)
    dut.stream_in_string.value = b"bytes"
    await cocotb.triggers.Timer(10, "ns")
    val = dut.stream_in_string.value
    assert isinstance(val, bytes)
    assert val == b"bytes"


@cocotb.skipif(
    LANGUAGE in ["verilog"] and SIM_NAME.startswith("riviera"),
    reason="Riviera is unhappy for an unknown reason",
)
@cocotb.xfail(
    SIM_NAME.startswith("icarus"),
    raises=AttributeError,
    reason="iverilog fails to discover string inputs (gh-2585)",
)
@cocotb.xfail(
    SIM_NAME.startswith("ghdl"),
    reason="GHDL fails to discover string input properly (gh-2584)",
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
        dut.stream_in_int.value = Immediate("1010 not a real binary string")
    with pytest.raises(TypeError):
        dut.stream_in_int.value = Immediate([])

    with pytest.raises(ValueError):
        dut.stream_in_int.value = "1010 not a real binary string"
    with pytest.raises(TypeError):
        dut.stream_in_int.value = []


@cocotb.xfail(
    SIM_NAME.startswith("icarus"),
    raises=AttributeError,
    reason="iverilog unable to find real signals (gh-2590)",
)
@cocotb.xfail(
    SIM_NAME.startswith("ghdl"),
    raises=AttributeError,
    reason="GHDL unable to find real signals (gh-2589)",
)
@cocotb.test
async def test_real_assign_double(dut):
    """
    Assign a random floating point value, read it back from the DUT and check
    it matches what we assigned
    """
    val = random.uniform(-1e307, 1e307)
    log = logging.getLogger("cocotb.test")
    timer_shortest = Timer(1, "step")
    await timer_shortest
    log.info("Setting the value %g", val)
    dut.stream_in_real.value = val
    await timer_shortest
    await timer_shortest  # FIXME: Workaround for VHPI scheduling - needs investigation
    got = dut.stream_out_real.value
    log.info("Read back value %g", got)
    assert got == val, "Values didn't match!"


@cocotb.xfail(
    SIM_NAME.startswith("icarus"),
    raises=AttributeError,
    reason="iverilog unable to find real signals (gh-2590)",
)
@cocotb.xfail(
    SIM_NAME.startswith("ghdl"),
    raises=AttributeError,
    reason="GHDL unable to find real signals (gh-2589)",
)
@cocotb.test
async def test_real_assign_int(dut):
    """Assign a random integer value to ensure we can write types convertible to
    int, read it back from the DUT and check it matches what we assigned.
    """
    val = random.randint(-(2**31), 2**31 - 1)
    log = logging.getLogger("cocotb.test")
    timer_shortest = Timer(1, "step")
    await timer_shortest
    log.info("Setting the value %i", val)
    dut.stream_in_real.value = val
    await timer_shortest
    await timer_shortest  # FIXME: Workaround for VHPI scheduling - needs investigation
    got = dut.stream_out_real.value
    log.info("Read back value %d", got)
    assert got == val, "Values didn't match!"


@cocotb.skipif(
    LANGUAGE == "vhdl", reason="identifiers starting with `_` are illegal in VHDL"
)
@cocotb.test
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


@cocotb.xfail(
    SIM_NAME.startswith("verilator"),
    reason="verilator does not support 4-state signals",
)
@cocotb.test
async def test_assign_Logic(dut):
    dut.stream_in_ready.value = Logic("X")
    await Timer(1, "ns")
    assert dut.stream_in_ready.value == "x"
    with pytest.raises(ValueError):
        dut.stream_in_data.value = Logic("U")  # not the correct size


@cocotb.skipif(
    LANGUAGE != "verilog" and not SIM_NAME.startswith("ghdl"),
    reason="For testing Verilog simulators, or GHDL which uses VPI",
)
@cocotb.skipif(
    SIM_NAME.startswith("verilator"), reason="Verilator only supports 2-state values."
)
@cocotb.test
async def test_assign_Logic_4value(dut):
    for value in ["X", "0", "1", "Z"]:
        dut.stream_in_ready.value = Logic(value)
        await Timer(1, "ns")
        assert dut.stream_in_ready.value == value


@cocotb.skipif(LANGUAGE != "vhdl", reason="For testing VHDL simulators.")
@cocotb.skipif(SIM_NAME.startswith("ghdl"), reason="GHDL only supports 4-state values.")
@cocotb.test
async def test_assign_Logic_9value(dut):
    for value in ["U", "X", "0", "1", "Z", "W", "L", "H", "-"]:
        dut.stream_in_ready.value = Logic(value)
        await Timer(1, "ns")
        assert dut.stream_in_ready.value == value


@cocotb.skipif(LANGUAGE != "vhdl", reason="For testing VHDL simulators.")
@cocotb.skipif(SIM_NAME.startswith("ghdl"), reason="GHDL only supports 4-state values.")
@cocotb.test
async def test_assign_LogicArray_9value(dut):
    # Reset to zero.
    dut.stream_in_data.value = LogicArray(0, 8)
    await Timer(1, "ns")
    assert dut.stream_in_data.value == 0

    # Write 8 values (except 0) and check.
    dut.stream_in_data.value = LogicArray("UX1ZWLH-")
    await Timer(1, "ns")
    assert dut.stream_in_data.value == LogicArray("UX1ZWLH-")


@cocotb.test
async def test_assign_string(dut):
    assert len(dut.stream_in_data) == 8
    cocotb.log.info("dut.stream_in_data type is %s", dut.stream_in_data._type)
    dut.stream_in_data.value = "10101010"
    await Timer(1, "ns")
    assert dut.stream_in_data.value == "10101010"
    with pytest.raises(ValueError):
        dut.stream_in_data.value = "XXX"  # not the correct size
    with pytest.raises(ValueError):
        dut.stream_in_data.value = "lol"  # not the correct values
    await Timer(1, "ns")
    assert dut.stream_in_data.value == "10101010"


@cocotb.skipif(LANGUAGE == "vhdl", reason="VHDL does not support immediate assignment.")
@cocotb.test
async def test_assign_immediate(dut):
    dut.mybits_uninitialized.value = Immediate(2)
    assert dut.mybits_uninitialized.value == 2

    dut.mybits_uninitialized.value = Immediate("01")
    assert dut.mybits_uninitialized.value == "01"

    dut.mybits_uninitialized.value = Immediate(LogicArray("11"))
    assert dut.mybits_uninitialized.value == LogicArray("11")


@cocotb.skipif(LANGUAGE == "vhdl", reason="VHDL does not support immediate assignment.")
@cocotb.test
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
        await ValueChange(dut.mybits_uninitialized)
        seen += 1
        dut.mybit.value = Immediate(0)
        nested.cancel()

    cocotb.start_soon(watch())
    await Timer(1, "ns")

    dut.mybits_uninitialized.value = Immediate(2)
    await Timer(1, "ns")
    assert seen == 1


@cocotb.xfail(
    SIM_NAME.startswith("ghdl"),
    reason="GHDL uses the VPI, which does not have a way to infer null ranges.",
)
@cocotb.xfail(
    SIM_NAME.startswith("modelsim")
    and os.getenv("VHDL_GPI_INTERFACE", "fli") == "vhpi",
    reason="Questa's implementation of the VHPI sets vhpiIsUpP incorrectly",
)
@cocotb.test
async def test_null_range_width(dut):
    # Normal arrays should have the same length regardless of language
    assert len(dut.array_7_downto_4) == 4
    if LANGUAGE in ["vhdl"]:
        # But in VHDL, `4 downto 7` should result in a null range
        assert len(dut.array_4_downto_7) == 0
    else:
        # Not so in (System)Verilog though
        assert len(dut.array_4_downto_7) == 4


@cocotb.test
async def test_assign_str_logic_scalar(dut) -> None:
    dut.stream_in_valid.value = 1
    await Timer(1, "ns")
    assert dut.stream_in_valid.value == "1"

    dut.stream_in_valid.value = "0"
    await Timer(1, "ns")
    assert dut.stream_in_valid.value == "0"

    dut.stream_in_valid.value = Logic("1")
    await Timer(1, "ns")
    assert dut.stream_in_valid.value == "1"

    dut.stream_in_valid.value = LogicArray("0")
    await Timer(1, "ns")
    assert dut.stream_in_valid.value == "0"

    with pytest.raises(TypeError):
        dut.stream_in_valid.value = (1, 0)  # not the correct type

    with pytest.raises(ValueError):
        dut.stream_in_valid.value = LogicArray("0101")  # too long

    with pytest.raises(ValueError):
        dut.stream_in_valid.value = "1010"  # too long

    # Veirlator doesn't support 4-state signals
    if not SIM_NAME.startswith("verilator"):
        dut.stream_in_valid.value = "Z"
        await Timer(1, "ns")
        assert dut.stream_in_valid.value == "Z"

    if LANGUAGE in ["vhdl"]:
        dut.stream_in_valid.value = "H"
        await Timer(1, "ns")
        assert dut.stream_in_valid.value == "H"


@cocotb.test
async def test_extended_identifiers(dut):
    if LANGUAGE == "vhdl":
        names = [
            "\\weird.signal(1)\\",
            "\\weird.signal(2)\\",
            "\\(.*|this looks like a regex)\\",
        ]
    elif SIM_NAME.startswith("icarus"):
        # Icarus normalizes extended identifier names to not include the
        # preceding \ or the trailing space
        names = [
            "weird.signal[1]",
            "weird.signal[2]",
            "(.*|this_looks_like_a_regex)",
        ]
    else:
        names = [
            "\\weird.signal[1] ",
            "\\weird.signal[2] ",
            "\\(.*|this_looks_like_a_regex) ",
        ]

    # Icarus, NVC, and Xcelium can't find the signals by name unless we scan
    # all signals
    dut._discover_all()

    # Debugging
    for name in dut._keys():
        cocotb.log.info("Found %r", name)

    for name in names:
        assert dut[name]._name == name


@cocotb.test
async def test_set_at_end_of_test(dut) -> None:
    """Tests that writes at the end of the test are still applied."""
    dut.stream_in_data.value = 0
    await Timer(1)
    dut.stream_in_data.value = 5


@cocotb.test
async def test_set_at_end_of_test_check(dut) -> None:
    assert dut.stream_in_data.value == 5


@cocotb.test
async def test_invalid_indexing(dut) -> None:
    # Indexing into packed arrays is not supported.
    with pytest.raises(TypeError):
        dut.stream_in_data[0]
    with pytest.raises(TypeError):
        dut.stream_in_data[0:1]

    # Slicing not supported by ArrayObject.
    with pytest.raises(TypeError):
        dut.array_7_downto_4[6:5]


@cocotb.test
async def test_setattr_error_msg(dut: Any) -> None:
    with pytest.raises(AttributeError, match=r"'example'.*[Nn]o.*exist"):
        dut.example = 1
    with pytest.raises(AttributeError, match=r"'stream_in_data'.*\.value"):
        dut.stream_in_data = 1


@cocotb.test
async def test_pickling_prohibited(dut: object) -> None:
    with pytest.raises(NotImplementedError):
        pickle.dumps(dut)


@cocotb.test
async def test_handle_str_with_separators(dut: Any) -> None:
    """Test that LogicArray handles string inputs with visual separators correctly."""
    dut.stream_in_data.value = "1010_1101"
    await Timer(1, "ns")
    assert dut.stream_in_data.value == LogicArray("10101101")

    dut.stream_in_data.value = "11__00__11__00"
    await Timer(1, "ns")
    assert dut.stream_in_data.value == LogicArray("11001100")

    dut.stream_in_data.value = "__01010011__"
    await Timer(1, "ns")
    assert dut.stream_in_data.value == LogicArray("01010011")
