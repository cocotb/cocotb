# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import cocotb
import pytest
from cocotb.binary import BinaryValue
from cocotb.triggers import Timer
from cocotb.handle import IntegerObject, ConstantObject, HierarchyObject, StringObject
from cocotb._sim_versions import IcarusVersion


# GHDL is unable to access signals in generate loops (gh-2594)
@cocotb.test(
    expect_error=IndexError if cocotb.SIM_NAME.lower().startswith("ghdl") else ())
async def pseudo_region_access(dut):
    """Test that pseudo-regions are accessible before iteration"""

    # Ensure pseudo-region lookup will fail
    if len(dut._sub_handles) != 0:
        dut._sub_handles = {}

    dut.genblk1[0]


@cocotb.test()
async def recursive_discover(dut):
    """Discover absolutely everything in the DUT"""
    def _discover(obj):
        for thing in obj:
            dut._log.debug("Found %s (%s)", thing._name, type(thing))
            _discover(thing)
    _discover(dut)


@cocotb.test()
async def discover_module_values(dut):
    """Discover everything in the DUT"""
    count = 0
    for thing in dut:
        count += 1
    assert count >= 2, "Expected to discover things in the DUT"


@cocotb.test()
async def discover_value_not_in_dut(dut):
    """Try and get a value from the DUT that is not there"""
    with pytest.raises(AttributeError):
        dut.fake_signal


@cocotb.test()
async def access_signal(dut):
    """Access a signal using the assignment mechanism"""
    dut.stream_in_data.setimmediatevalue(1)
    await Timer(1, "ns")
    assert dut.stream_in_data.value.integer == 1


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def access_type_bit_verilog(dut):
    """Access type bit in SystemVerilog"""
    await Timer(1, "step")
    assert dut.mybit.value == 1, "The default value was incorrect"
    dut.mybit.value = 0
    await Timer(1, "ns")
    assert dut.mybit.value == 0, "The assigned value was incorrect"

    assert dut.mybits.value == 0b11, "The default value was incorrect"
    dut.mybits.value = 0b00
    await Timer(1, "ns")
    assert dut.mybits.value == 0b00, "The assigned value was incorrect"

    assert dut.mybits_uninitialized.value == 0b00, "The default value was incorrect"
    dut.mybits_uninitialized.value = 0b11
    await Timer(1, "ns")
    assert dut.mybits_uninitialized.value == 0b11, "The assigned value was incorrect"


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def access_type_bit_verilog_metavalues(dut):
    """Access type bit in SystemVerilog with metavalues that the type does not support.

    Note that some simulators (wrongly) allow metavalues even for bits when taking the VPI route.
    The metavalues still may show up as `0` and `1` in HDL (Xcelium and Riviera).
    """
    await Timer(1, "ns")
    dut.mybits.value = BinaryValue("XZ")
    await Timer(1, "ns")
    print(dut.mybits.value.binstr)
    if cocotb.SIM_NAME.lower().startswith(("icarus", "ncsim", "xmsim")):
        assert dut.mybits.value.binstr.lower() == "xz", "The assigned value was not as expected"
    elif cocotb.SIM_NAME.lower().startswith(("riviera",)):
        assert dut.mybits.value.binstr.lower() == "10", "The assigned value was not as expected"
    else:
        assert dut.mybits.value.binstr.lower() == "00", "The assigned value was incorrect"

    dut.mybits.value = BinaryValue("ZX")
    await Timer(1, "ns")
    print(dut.mybits.value.binstr)
    if cocotb.SIM_NAME.lower().startswith(("icarus", "ncsim", "xmsim")):
        assert dut.mybits.value.binstr.lower() == "zx", "The assigned value was not as expected"
    elif cocotb.SIM_NAME.lower().startswith(("riviera",)):
        assert dut.mybits.value.binstr.lower() == "01", "The assigned value was not as expected"
    else:
        assert dut.mybits.value.binstr.lower() == "00", "The assigned value was incorrect"


@cocotb.test(
    # Icarus up to (and including) 10.3 doesn't support bit-selects, see https://github.com/steveicarus/iverilog/issues/323
    expect_error=IndexError if (cocotb.SIM_NAME.lower().startswith("icarus") and (IcarusVersion(cocotb.SIM_VERSION) <= IcarusVersion("10.3 (stable)"))) else (),
    skip=cocotb.LANGUAGE in ["vhdl"])
async def access_single_bit(dut):
    """Access a single bit in a vector of the DUT"""
    dut.stream_in_data.value = 0
    await Timer(1, "ns")
    dut.stream_in_data[2].value = 1
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value.integer == (1 << 2)


@cocotb.test()
async def access_single_bit_erroneous(dut):
    """Access a non-existent single bit"""
    with pytest.raises(IndexError):
        dut.stream_in_data[100000]


# Riviera discovers integers as nets (gh-2597)
# GHDL discovers integers as nets (gh-2596)
# Icarus does not support integer signals (gh-2598)
@cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith(("icarus", "chronologic simulation vcs"))
    else (),
    expect_fail=(
        cocotb.SIM_NAME.lower().startswith("riviera")
        and cocotb.LANGUAGE in ["verilog"]
        or cocotb.SIM_NAME.lower().startswith("ghdl")
    ),
)
async def access_integer(dut):
    """Integer should show as an IntegerObject"""
    assert isinstance(dut.stream_in_int, IntegerObject)

    with pytest.raises(IndexError):
        dut.stream_in_int[3]

    assert len(dut.stream_in_int) == 1


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
async def access_ulogic(dut):
    """Access a std_ulogic as enum"""
    dut.stream_in_valid


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
async def access_constant_integer(dut):
    """
    Access a constant integer
    """
    assert isinstance(dut.isample_module1.EXAMPLE_WIDTH, ConstantObject)
    assert dut.isample_module1.EXAMPLE_WIDTH == 7


# GHDL inexplicably crashes, so we will skip this test for now
# likely has to do with overall poor support of string over the VPI
@cocotb.test(
    skip=cocotb.LANGUAGE in ["verilog"] or cocotb.SIM_NAME.lower().startswith("ghdl"))
async def access_constant_string_vhdl(dut):
    """Access to a string, both constant and signal."""
    constant_string = dut.isample_module1.EXAMPLE_STRING
    assert isinstance(constant_string, ConstantObject)
    assert constant_string.value == b"TESTING"


# GHDL discovers strings as vpiNetArray (gh-2584)
@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"],
             expect_error=TypeError if cocotb.SIM_NAME.lower().startswith("ghdl") else ())
async def test_writing_string_undersized(dut):
    test_string = b"cocotb"
    dut.stream_in_string.setimmediatevalue(test_string)
    assert dut.stream_out_string == b''
    await Timer(1, "ns")
    assert dut.stream_out_string.value == test_string


# GHDL discovers strings as vpiNetArray (gh-2584)
@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"],
             expect_error=TypeError if cocotb.SIM_NAME.lower().startswith("ghdl") else ())
async def test_writing_string_oversized(dut):
    test_string = b"longer_than_the_array"
    dut.stream_in_string.setimmediatevalue(test_string)
    await Timer(1, "ns")
    assert dut.stream_out_string.value == test_string[:len(dut.stream_out_string)]


# GHDL discovers strings as vpiNetArray (gh-2584)
@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"],
             expect_error=TypeError if cocotb.SIM_NAME.lower().startswith("ghdl") else ())
async def test_read_single_character(dut):
    test_string = b"cocotb!!!"
    idx = 3
    dut.stream_in_string.setimmediatevalue(test_string)
    await Timer(1, "ns")
    # String is defined as string(1 to 8) so idx=3 will access the 3rd character
    assert dut.stream_out_string[idx].value == test_string[idx - 1]


# GHDL discovers strings as vpiNetArray (gh-2584)
@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"],
             expect_error=TypeError if cocotb.SIM_NAME.lower().startswith("ghdl") else ())
async def test_write_single_character(dut):
    # set initial value
    test_string = b"verilog0"
    dut.stream_in_string.setimmediatevalue(test_string)
    await Timer(1, "ns")

    # iterate over each character handle and uppercase it
    for c in dut.stream_in_string:
        lowercase = chr(c)
        uppercase = lowercase.upper()
        uppercase_as_int = ord(uppercase)
        c.setimmediatevalue(uppercase_as_int)
    await Timer(1, "ns")

    # test the output is uppercased
    assert dut.stream_out_string.value == test_string.upper()


# TODO: add tests for Verilog "string_input_port" and "STRING_LOCALPARAM" (see issue #802)

@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"] or cocotb.SIM_NAME.lower().startswith("riviera"),
             expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith("icarus") else ())
async def access_const_string_verilog(dut):
    """Access to a const Verilog string."""

    await Timer(10, "ns")
    assert isinstance(dut.STRING_CONST, StringObject)
    assert dut.STRING_CONST == b"TESTING_CONST"

    dut.STRING_CONST.value = b"MODIFIED"
    await Timer(10, "ns")
    assert dut.STRING_CONST != b"TESTING_CONST"


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"],
             expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith("icarus") else ())
async def access_var_string_verilog(dut):
    """Access to a var Verilog string."""

    await Timer(10, "ns")
    assert isinstance(dut.STRING_VAR, StringObject)
    assert dut.STRING_VAR == b"TESTING_VAR"

    dut.STRING_VAR.value = b"MODIFIED"
    await Timer(10, "ns")
    assert dut.STRING_VAR == b"MODIFIED"


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
async def access_constant_boolean(dut):
    """Test access to a constant boolean"""
    assert isinstance(dut.isample_module1.EXAMPLE_BOOL, ConstantObject)
    assert dut.isample_module1.EXAMPLE_BOOL.value == True  # noqa


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
async def access_boolean(dut):
    """Test access to a boolean"""

    with pytest.raises(IndexError):
        dut.stream_in_bool[3]

    assert len(dut.stream_in_bool) == 1

    curr_val = dut.stream_in_bool.value
    dut.stream_in_bool.setimmediatevalue(not curr_val)
    await Timer(1, "ns")
    assert curr_val != dut.stream_out_bool.value


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def access_internal_register_array(dut):
    """Test access to an internal register array"""

    assert dut.register_array[0].value.binstr == "xxxxxxxx", \
        "Failed to access internal register array value"

    dut.register_array[1].setimmediatevalue(4)
    await Timer(1, "ns")
    assert dut.register_array[1].value == 4, \
        "Failed to set internal register array value"


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"],
             expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith("icarus") else ())
async def access_gate(dut):
    """
    Test access to a gate Object
    """
    assert isinstance(dut.test_and_gate, HierarchyObject)


# GHDL is unable to access record types (gh-2591)
@cocotb.test(
    skip=cocotb.LANGUAGE in ["verilog"],
    expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith("ghdl") else ())
async def custom_type(dut):
    """
    Test iteration over a custom type
    """
    expected_sub = 84
    expected_top = 4

    count = 0

    def _discover(obj):
        iter_count = 0
        for elem in obj:
            iter_count += 1
            iter_count += _discover(elem)
        return iter_count

    for sub in dut.cosLut:
        sub_count = _discover(sub)
        assert sub_count == expected_sub
        count += 1

    assert expected_top == count


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def type_check_verilog(dut):
    """
    Test if types are recognized
    """

    test_handles = [
        (dut.stream_in_ready, "GPI_REGISTER"),
        (dut.register_array, "GPI_ARRAY"),
        (dut.temp, "GPI_REGISTER"),
        (dut.and_output, "GPI_NET"),
        (dut.stream_in_data, "GPI_NET"),
        (dut.logic_b, "GPI_REGISTER"),
        (dut.logic_c, "GPI_REGISTER"),
        (dut.INT_PARAM, "GPI_INTEGER"),
        (dut.REAL_PARAM, "GPI_REAL"),
        (dut.STRING_PARAM, "GPI_STRING")
    ]

    if cocotb.SIM_NAME.lower().startswith("icarus"):
        test_handles.append((dut.logic_a, "GPI_NET"))  # https://github.com/steveicarus/iverilog/issues/312
    else:
        test_handles.append((dut.logic_a, "GPI_REGISTER"))

    for handle in test_handles:
        assert handle[0]._type == handle[1]
