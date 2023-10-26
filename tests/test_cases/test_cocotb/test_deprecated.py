# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import pytest

import cocotb
from cocotb.triggers import Timer


# strings are not supported on Icarus (gh-2585) or GHDL (gh-2584)
@cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith("icarus")
    else TypeError
    if cocotb.SIM_NAME.lower().startswith("ghdl")
    else ()
)
async def test_unicode_handle_assignment_deprecated(dut):
    with pytest.warns(DeprecationWarning, match=".*bytes.*"):
        dut.stream_in_string.value = "Bad idea"
        await cocotb.triggers.ReadWrite()


@cocotb.test()
async def test_convert_handle_to_string_deprecated(dut):
    dut.stream_in_data.value = 0
    await cocotb.triggers.Timer(1, units="ns")

    with pytest.warns(FutureWarning, match=".*_path.*"):
        as_str = str(dut.stream_in_data)

    # in future this will be ` == dut._path`
    assert as_str == str(dut.stream_in_data.value)

    if cocotb.LANGUAGE == "verilog":
        # the `NUM_OF_MODULES` parameter is only present in the verilog design
        with pytest.warns(FutureWarning, match=".*_path.*"):
            as_str = str(dut.NUM_OF_MODULES)

        # in future this will be ` == dut._path`
        assert as_str == str(dut.NUM_OF_MODULES.value)


@cocotb.test()
async def test_time_ps_deprecated(_):
    with pytest.warns(DeprecationWarning):
        Timer(time_ps=7, units="ns")
    with pytest.raises(TypeError):
        Timer(time=0, time_ps=7, units="ns")
    with pytest.raises(TypeError):
        Timer(units="ps")
