# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for handles
"""
import cocotb
from cocotb.result import TestFailure


@cocotb.test()
def test_lessthan_raises_error(dut):
    """
    Test that trying to use <= as if it were a comparison produces an error
    """
    ret = dut.stream_in_data <= 0x12
    try:
        bool(ret)
    except TypeError:
        pass
    else:
        raise TestFailure(
            "No exception was raised when confusing comparison with assignment"
        )

    # to make this a generator
    if False: yield


@cocotb.test()
def test_bad_attr(dut):
    yield cocotb.triggers.NullTrigger()
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
