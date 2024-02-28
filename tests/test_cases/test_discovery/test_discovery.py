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

import os

import pytest

import cocotb
from cocotb._sim_versions import VerilatorVersion
from cocotb.handle import (
    ArrayObject,
    HierarchyObject,
    HierarchyObjectBase,
    IntegerObject,
    StringObject,
)
from cocotb.triggers import Timer
from cocotb.types import LogicArray

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


# GHDL is unable to access signals in generate loops (gh-2594)
# Verilator doesn't support vpiGenScope or vpiGenScopeArray (gh-1884)
@cocotb.test(
    expect_error=IndexError
    if SIM_NAME.startswith("ghdl")
    else AttributeError
    if SIM_NAME.startswith("verilator")
    else ()
)
async def pseudo_region_access(dut):
    """Test that pseudo-regions are accessible before iteration"""

    # Ensure pseudo-region lookup will fail
    if len(dut._sub_handles) != 0:
        dut._sub_handles = {}

    dut.genblk1[0]


def verilog_test(skip=False, **kwargs):
    return cocotb.test(skip=skip or LANGUAGE in ["vhdl"], **kwargs)


verilator_less_than_5024 = SIM_NAME.startswith("verilator") and VerilatorVersion(
    cocotb.SIM_VERSION
) < VerilatorVersion("5.024")


@verilog_test(expect_error=AttributeError if verilator_less_than_5024 else ())
async def test_cond_scope(dut):
    assert dut.cond_scope.scoped_sub._path == f"{dut._path}.cond_scope.scoped_sub"


@verilog_test(expect_error=AttributeError)
async def test_bad_var(dut):
    print(dut.cond_scope_else_asdf._path)


@verilog_test(expect_error=AttributeError if SIM_NAME.startswith("verilator") else ())
async def test_arr_scope(dut):
    assert dut.arr[1].arr_sub._path == f"{dut._path}.arr[1].arr_sub"


@verilog_test(expect_error=AttributeError if verilator_less_than_5024 else ())
async def test_nested_scope(dut):
    assert (
        dut.outer_scope[1].inner_scope[1]._path
        == f"{dut._path}.outer_scope[1].inner_scope[1]"
    )


@verilog_test(
    expect_error=AttributeError if verilator_less_than_5024 else (),
)
async def test_scoped_params(dut):
    assert dut.cond_scope.scoped_param.value == 1
    assert dut.outer_scope[1].outer_param.value == 2
    assert dut.outer_scope[1].inner_scope[1].inner_param.value == 3


@verilog_test(
    expect_error=AttributeError if verilator_less_than_5024 else (),
    expect_fail=SIM_NAME.startswith("riviera"),
)
async def test_intf_array(dut):
    assert len(dut.intf_arr) == 2
    for i, intf in enumerate(dut.intf_arr):
        assert intf._name == f"intf_arr[{i}]"
        assert intf._path == f"{dut._path}.intf_arr[{i}]"


@cocotb.test()
async def recursive_discover(dut):
    """Discover absolutely everything in the DUT"""

    def _discover(obj):
        if not isinstance(obj, (HierarchyObject, ArrayObject)):
            return
        for thing in obj:
            dut._log.debug("Found %s (%s)", thing._name, type(thing))
            _discover(thing)

    _discover(dut)


class ScopeMissingError(Exception):
    pass


class ScopeModuleMissingError(Exception):
    pass


@verilog_test(
    expect_error=ScopeMissingError,
    skip=verilator_less_than_5024,
)
async def test_both_conds(dut):
    """
    Xcelium returns invalid scopes with vpi_handle_by_name(), which will segfault if iterated
    This is now accounted for in VpiImpl.cpp
    """
    assert dut.cond_scope.scoped_sub._path == f"{dut._path}.cond_scope.scoped_sub"

    try:
        print(dut.cond_scope_else._path)
    except AttributeError as e:
        raise ScopeMissingError from e

    try:
        print(dut.cond_scope_else.scoped_sub_else._path)
    except AttributeError as e:
        raise ScopeModuleMissingError from e


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
    assert dut.stream_in_data.value == 1


@cocotb.test(skip=LANGUAGE in ["vhdl"])
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


@cocotb.test(skip=LANGUAGE in ["vhdl"])
async def access_type_bit_verilog_metavalues(dut):
    """Access type bit in SystemVerilog with metavalues that the type does not support.

    Note that some simulators (wrongly) allow metavalues even for bits when taking the VPI route.
    The metavalues still may show up as `0` and `1` in HDL (Xcelium and Riviera).
    """
    await Timer(1, "ns")
    dut.mybits.value = LogicArray("XZ")
    await Timer(1, "ns")
    if SIM_NAME.startswith(("icarus", "ncsim", "xmsim")):
        assert dut.mybits.value == "xz"
    elif SIM_NAME.startswith(("riviera",)):
        assert dut.mybits.value == "10"
    else:
        assert dut.mybits.value == "00"

    dut.mybits.value = LogicArray("ZX")
    await Timer(1, "ns")
    if SIM_NAME.startswith(("icarus", "ncsim", "xmsim")):
        assert dut.mybits.value == "zx"
    elif SIM_NAME.startswith(("riviera",)):
        assert dut.mybits.value == "01"
    else:
        assert dut.mybits.value == "00"


# Riviera discovers integers as nets (gh-2597)
# GHDL discovers integers as nets (gh-2596)
# Icarus does not support integer signals (gh-2598)
@cocotb.test(
    expect_error=AttributeError
    if SIM_NAME.startswith(("icarus", "chronologic simulation vcs"))
    else (),
    expect_fail=(
        SIM_NAME.startswith("riviera")
        and LANGUAGE in ["verilog"]
        or SIM_NAME.startswith(("ghdl", "verilator"))
    ),
)
async def access_integer(dut):
    """Integer should show as an IntegerObject"""
    assert isinstance(dut.stream_in_int, IntegerObject)


@cocotb.test(skip=LANGUAGE in ["verilog"])
async def access_ulogic(dut):
    """Access a std_ulogic as enum"""
    dut.stream_in_valid


# GHDL discovers generics as vpiParameter (gh-2722)
@cocotb.test(
    skip=LANGUAGE in ["verilog"],
    expect_error=NotImplementedError if SIM_NAME.startswith("ghdl") else (),
)
async def access_constant_integer(dut):
    """
    Access a constant integer
    """
    assert isinstance(dut.isample_module1.EXAMPLE_WIDTH, IntegerObject)
    assert dut.isample_module1.EXAMPLE_WIDTH.value == 7


# GHDL discovers generics as vpiParameter (gh-2722)
@cocotb.test(
    skip=LANGUAGE in ["verilog"],
    expect_error=NotImplementedError if SIM_NAME.startswith("ghdl") else (),
)
async def access_constant_string_vhdl(dut):
    """Access to a string, both constant and signal."""
    constant_string = dut.isample_module1.EXAMPLE_STRING
    assert isinstance(constant_string, StringObject)
    assert constant_string.value == b"TESTING"


# GHDL discovers strings as vpiNetArray (gh-2584)
@cocotb.test(
    skip=LANGUAGE in ["verilog"],
    expect_fail=SIM_NAME.startswith("ghdl"),
)
async def test_writing_string_undersized(dut):
    assert isinstance(dut.stream_in_string, StringObject)
    test_string = b"cocotb"
    dut.stream_in_string.setimmediatevalue(test_string)
    assert dut.stream_out_string.value == b""
    await Timer(1, "ns")
    assert dut.stream_out_string.value == test_string


# GHDL discovers strings as vpiNetArray (gh-2584)
@cocotb.test(
    skip=LANGUAGE in ["verilog"],
    expect_fail=SIM_NAME.startswith("ghdl"),
)
async def test_writing_string_oversized(dut):
    assert isinstance(dut.stream_in_string, StringObject)
    test_string = b"longer_than_the_array"
    dut.stream_in_string.setimmediatevalue(test_string)
    await Timer(1, "ns")
    assert dut.stream_out_string.value == test_string[: len(dut.stream_out_string)]


# TODO: add tests for Verilog "string_input_port" and "STRING_LOCALPARAM" (see issue #802)


@cocotb.test(
    skip=LANGUAGE in ["vhdl"] or SIM_NAME.startswith("riviera"),
    expect_error=AttributeError if SIM_NAME.startswith("icarus") else (),
)
async def access_const_string_verilog(dut):
    """Access to a const Verilog string."""

    await Timer(10, "ns")
    assert isinstance(dut.STRING_CONST, StringObject)
    assert dut.STRING_CONST.value == b"TESTING_CONST"

    dut.STRING_CONST.value = b"MODIFIED"
    await Timer(10, "ns")
    assert dut.STRING_CONST.value != b"TESTING_CONST"


@cocotb.test(
    skip=LANGUAGE in ["vhdl"],
    expect_error=AttributeError if SIM_NAME.startswith("icarus") else (),
)
async def access_var_string_verilog(dut):
    """Access to a var Verilog string."""

    await Timer(10, "ns")
    assert isinstance(dut.STRING_VAR, StringObject)
    assert dut.STRING_VAR.value == b"TESTING_VAR"

    dut.STRING_VAR.value = b"MODIFIED"
    await Timer(10, "ns")
    assert dut.STRING_VAR.value == b"MODIFIED"


# GHDL discovers generics as vpiParameter (gh-2722)
@cocotb.test(
    skip=LANGUAGE in ["verilog"],
    expect_error=NotImplementedError if SIM_NAME.startswith("ghdl") else (),
)
async def access_constant_boolean(dut):
    """Test access to a constant boolean"""
    assert isinstance(dut.isample_module1.EXAMPLE_BOOL, IntegerObject)
    assert dut.isample_module1.EXAMPLE_BOOL.value == True  # noqa


# GHDL discovers booleans as vpiNet (gh-2596)
@cocotb.test(
    skip=LANGUAGE in ["verilog"],
    expect_fail=SIM_NAME.startswith("ghdl"),
)
async def access_boolean(dut):
    """Test access to a boolean"""
    assert isinstance(dut.stream_out_bool, IntegerObject)

    curr_val = dut.stream_in_bool.value
    dut.stream_in_bool.setimmediatevalue(not curr_val)
    await Timer(1, "ns")
    assert curr_val != dut.stream_out_bool.value


@cocotb.test(skip=LANGUAGE in ["vhdl"])
async def access_internal_register_array(dut):
    """Test access to an internal register array"""

    dut.register_array[1].value = 4
    await Timer(1, "ns")
    assert dut.register_array[1].value == 4


@cocotb.test(
    skip=LANGUAGE in ["vhdl"],
    expect_error=AttributeError if SIM_NAME.startswith(("icarus", "verilator")) else (),
)
async def access_gate(dut):
    """
    Test access to a gate Object
    """
    assert isinstance(dut.test_and_gate, HierarchyObject)


# GHDL is unable to access record types (gh-2591)
@cocotb.test(
    skip=LANGUAGE in ["verilog"],
    expect_error=AttributeError if SIM_NAME.startswith("ghdl") else (),
)
async def custom_type(dut):
    """
    Test iteration over a custom type
    """
    # Hardcoded to ensure correctness
    expected_inner = 7
    expected_outer = 4
    expected_elem = 11

    outer_count = 0
    for inner_array in dut.cosLut:
        inner_count = 0
        for elem in inner_array:
            assert len(elem) == expected_elem
            inner_count += 1
        assert inner_count == expected_inner
        outer_count += 1
    assert expected_outer == outer_count


@cocotb.test(skip=LANGUAGE in ["vhdl"])
async def type_check_verilog(dut):
    """
    Test if types are recognized
    """

    test_handles = [
        (dut.stream_in_ready, "GPI_REGISTER"),
        (dut.register_array, "GPI_ARRAY"),
        (dut.temp, "GPI_REGISTER"),
        (dut.logic_b, "GPI_REGISTER"),
        (dut.logic_c, "GPI_REGISTER"),
        (dut.INT_PARAM, "GPI_REGISTER"),
        (dut.REAL_PARAM, "GPI_REAL"),
    ]

    if SIM_NAME.startswith("icarus"):
        test_handles.append(
            (dut.logic_a, "GPI_NET")
        )  # https://github.com/steveicarus/iverilog/issues/312
    else:
        test_handles.append((dut.logic_a, "GPI_REGISTER"))

    # Verilator returns vpiReg rather than vpiNet
    # Verilator (correctly) treats parameters with implicit type, that are assigned a string literal value, as an unsigned integer. See IEEE 1800-2017 Section 5.9 and Section 6.20.2
    if SIM_NAME.startswith("verilator"):
        test_handles.append((dut.stream_in_data, "GPI_REGISTER"))
        test_handles.append((dut.and_output, "GPI_REGISTER"))
        test_handles.append((dut.STRING_PARAM, "GPI_REGISTER"))
    else:
        test_handles.append((dut.stream_in_data, "GPI_NET"))
        test_handles.append((dut.and_output, "GPI_NET"))
        test_handles.append((dut.STRING_PARAM, "GPI_STRING"))

    for handle in test_handles:
        assert handle[0]._type == handle[1]


# GHDL cannot find signal in "block" statement, may be related to (gh-2594)
@cocotb.test(
    skip=LANGUAGE in ["verilog"],
    expect_error=AttributeError if SIM_NAME.startswith("ghdl") else (),
)
async def access_block_vhdl(dut):
    """Access a VHDL block statement"""

    dut.isample_module1.SAMPLE_BLOCK
    dut.isample_module1.SAMPLE_BLOCK.clk_inv


@cocotb.test(skip=LANGUAGE in ["verilog"])
async def discover_all_in_component_vhdl(dut):
    """Access a non local indexed name"""

    questa_vhpi = (
        SIM_NAME.startswith("modelsim")
        and os.getenv("VHDL_GPI_INTERFACE", "fli") == "vhpi"
    )

    def _discover(obj):
        if questa_vhpi and isinstance(obj, StringObject):
            # Iterating over the elements of a string with Questa's VHPI causes a stacktrace
            return 0
        if not isinstance(obj, (HierarchyObjectBase, ArrayObject)):
            return 0
        count = 0
        for thing in obj:
            count += 1
            dut._log.info("Found %s (%s)", thing._path, type(thing))
            count += _discover(thing)
        return count

    total_count = _discover(dut.isample_module1)

    sim = SIM_NAME

    # ideally should be 9:
    #   1   EXAMPLE_STRING
    #   1   EXAMPLE_BOOL
    #   1   EXAMPLE_WIDTH
    #   1   clk
    #   1   stream_in_data
    #   1   stream_out_data_registered
    #   1   stream_out_data_valid
    #   1   SAMPLE_BLOCK
    #   1   SAMPLE_BLOCK.clk_inv
    if sim.startswith("ghdl"):
        # finds SAMPLE_BLOCK twice
        # doesn't find EXAMPLE_STRING, EXAMPLE_BOOL, or EXAMPLE_WIDTH
        assert total_count == 7
    elif sim.startswith("nvc"):
        # finds SAMPLE_BLOCK.clk_inv twice?
        assert total_count == 10
    else:
        assert total_count == 9
