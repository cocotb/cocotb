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
import logging
import pytest
from cocotb.binary import BinaryValue
from cocotb.triggers import Timer
from cocotb.result import TestError, TestFailure
from cocotb.handle import IntegerObject, ConstantObject, HierarchyObject, StringObject
from cocotb._sim_versions import IcarusVersion


# GHDL unable to access signals in generate loops (gh-2594)
@cocotb.test(
    expect_error=IndexError if cocotb.SIM_NAME.lower().startswith("ghdl") else ())
async def pseudo_region_access(dut):
    """Test that pseudo-regions are accessible before iteration"""

    # Ensure pseudo-region lookup will fail
    if len(dut._sub_handles) != 0:
        dut._sub_handles = {}

    pseudo_region = dut.genblk1
    dut._log.info("Found %s (%s)", pseudo_region._name, type(pseudo_region))
    first_generate_instance = pseudo_region[0]
    dut._log.info("Found %s (%s)", first_generate_instance._name, type(first_generate_instance))


@cocotb.test()
async def recursive_discover(dut):
    """Discover absolutely everything in the DUT"""
    def _discover(obj):
        for thing in obj:
            dut._log.info("Found %s (%s)", thing._name, type(thing))
            _discover(thing)
    _discover(dut)


@cocotb.test()
async def discover_module_values(dut):
    """Discover everything in the DUT"""
    count = 0
    for thing in dut:
        thing._log.info("Found something: %s" % thing._fullname)
        count += 1
    if count < 2:
        raise TestFailure("Expected to discover things in the DUT")


@cocotb.test()
async def discover_value_not_in_dut(dut):
    """Try and get a value from the DUT that is not there"""
    with pytest.raises(AttributeError):
        fake_signal = dut.fake_signal


@cocotb.test()
async def access_signal(dut):
    """Access a signal using the assignment mechanism"""
    tlog = logging.getLogger("cocotb.test")
    signal = dut.stream_in_data

    tlog.info("Signal is %s" % type(signal))
    dut.stream_in_data.setimmediatevalue(1)
    await Timer(1, "ns")
    if dut.stream_in_data.value.integer != 1:
        raise TestError("%s.%s != %d" %
                        (dut.stream_in_data._path,
                         dut.stream_in_data.value.integer, 1))


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def access_type_bit_verilog(dut):
    """Access type bit in SystemVerilog"""
    await Timer(1, "step")
    assert dut.mybit.value == 1, "The default value was incorrect"
    dut.mybit <= 0
    await Timer(1, "ns")
    assert dut.mybit.value == 0, "The assigned value was incorrect"

    assert dut.mybits.value == 0b11, "The default value was incorrect"
    dut.mybits <= 0b00
    await Timer(1, "ns")
    assert dut.mybits.value == 0b00, "The assigned value was incorrect"

    assert dut.mybits_uninitialized.value == 0b00, "The default value was incorrect"
    dut.mybits_uninitialized <= 0b11
    await Timer(1, "ns")
    assert dut.mybits_uninitialized.value == 0b11, "The assigned value was incorrect"


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def access_type_bit_verilog_metavalues(dut):
    """Access type bit in SystemVerilog with metavalues that the type does not support.

    Note that some simulators (wrongly) allow metavalues even for bits when taking the VPI route.
    The metavalues still may show up as `0` and `1` in HDL (Xcelium and Riviera).
    """
    await Timer(1, "ns")
    dut.mybits <= BinaryValue("XZ")
    await Timer(1, "ns")
    print(dut.mybits.value.binstr)
    if cocotb.SIM_NAME.lower().startswith(("icarus", "ncsim", "xmsim")):
        assert dut.mybits.value.binstr.lower() == "xz", "The assigned value was not as expected"
    elif cocotb.SIM_NAME.lower().startswith(("riviera",)):
        assert dut.mybits.value.binstr.lower() == "10", "The assigned value was not as expected"
    else:
        assert dut.mybits.value.binstr.lower() == "00", "The assigned value was incorrect"

    dut.mybits <= BinaryValue("ZX")
    await Timer(1, "ns")
    print(dut.mybits.value.binstr)
    if cocotb.SIM_NAME.lower().startswith(("icarus", "ncsim", "xmsim")):
        assert dut.mybits.value.binstr.lower() == "zx", "The assigned value was not as expected"
    elif cocotb.SIM_NAME.lower().startswith(("riviera",)):
        assert dut.mybits.value.binstr.lower() == "01", "The assigned value was not as expected"
    else:
        assert dut.mybits.value.binstr.lower() == "00", "The assigned value was incorrect"


@cocotb.test(
    # Icarus up to (including) 10.3 doesn't support bit-selects, see https://github.com/steveicarus/iverilog/issues/323
    expect_error=IndexError if (cocotb.SIM_NAME.lower().startswith("icarus") and (IcarusVersion(cocotb.SIM_VERSION) <= IcarusVersion("10.3 (stable)"))) else (),
    skip=cocotb.LANGUAGE in ["vhdl"])
async def access_single_bit(dut):
    """Access a single bit in a vector of the DUT"""
    dut.stream_in_data <= 0
    await Timer(1, "ns")
    dut._log.info("%s = %d bits" %
                  (dut.stream_in_data._path, len(dut.stream_in_data)))
    dut.stream_in_data[2] <= 1
    await Timer(1, "ns")
    if dut.stream_out_data_comb.value.integer != (1 << 2):
        raise TestError("%s.%s != %d" %
                        (dut.stream_out_data_comb._path,
                         dut.stream_out_data_comb.value.integer, (1 << 2)))


@cocotb.test(expect_error=IndexError)
async def access_single_bit_erroneous(dut):
    """Access a non-existent single bit"""
    dut._log.info("%s = %d bits" %
                  (dut.stream_in_data._path, len(dut.stream_in_data)))
    bit = len(dut.stream_in_data) + 4
    dut.stream_in_data[bit] <= 1


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
    bitfail = False
    tlog = logging.getLogger("cocotb.test")
    test_int = dut.stream_in_int
    if not isinstance(test_int, IntegerObject):
        raise TestFailure("dut.stream_in_int is not an integer but {} instead".format(type(test_int)))

    try:
        bit = test_int[3]
    except IndexError as e:
        tlog.info("Access to bit is an error as expected")
        bitfail = True

    if not bitfail:
        raise TestFailure("Access into an integer should be invalid")

    length = len(test_int)
    if length != 1:
        raise TestFailure("Length should be 1 not %d" % length)


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
async def access_ulogic(dut):
    """Access a std_ulogic as enum"""
    constant_integer = dut.stream_in_valid


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
async def access_constant_integer(dut):
    """
    Access a constant integer
    """
    tlog = logging.getLogger("cocotb.test")
    constant_integer = dut.isample_module1.EXAMPLE_WIDTH
    tlog.info("Value of EXAMPLE_WIDTH is %d" % constant_integer)
    if not isinstance(constant_integer, ConstantObject):
        raise TestFailure("EXAMPLE_WIDTH was not constant")
    if constant_integer != 7:
        raise TestFailure("EXAMPLE_WIDTH was not 7")


# GHDL inexplicably crashes, so we will skip this test for now
# likely has to do with overall poor support of string over the VPI
@cocotb.test(
    skip=cocotb.LANGUAGE in ["verilog"] or cocotb.SIM_NAME.lower().startswith("ghdl"))
async def access_string_vhdl(dut):
    """Access to a string, both constant and signal."""
    tlog = logging.getLogger("cocotb.test")
    constant_string = dut.isample_module1.EXAMPLE_STRING
    tlog.info(f"{constant_string!r} is {constant_string.value}")
    if not isinstance(constant_string, ConstantObject):
        raise TestFailure("EXAMPLE_STRING was not constant")
    if constant_string != b"TESTING":
        raise TestFailure("EXAMPLE_STRING was not == \'TESTING\'")

    tlog.info("Test writing under size")

    test_string = b"cocotb"
    dut.stream_in_string.setimmediatevalue(test_string)

    variable_string = dut.stream_out_string
    if variable_string != b'':
        raise TestFailure("%r not \'\'" % variable_string)

    await Timer(1, "ns")

    if variable_string != test_string:
        raise TestFailure(f"{variable_string!r} {variable_string.value} != '{test_string}'")

    test_string = b"longer_than_the_array"
    tlog.info("Test writing over size with '%s'" % test_string)

    dut.stream_in_string.setimmediatevalue(test_string)
    variable_string = dut.stream_out_string

    await Timer(1, "ns")

    test_string = test_string[:len(variable_string)]

    if variable_string != test_string:
        raise TestFailure(f"{variable_string!r} {variable_string.value} != '{test_string}'")

    tlog.info("Test read access to a string character")

    await Timer(1, "ns")

    idx = 3

    result_slice = variable_string[idx]

    # String is defined as string(1 to 8) so idx=3 will access the 3rd character
    if result_slice != test_string[idx - 1]:
        raise TestFailure("Single character did not match {} != {}".format(result_slice, test_string[idx - 1]))

    tlog.info("Test write access to a string character")

    await Timer(1, "ns")

    for i in variable_string:
        lower = chr(i)
        upper = lower.upper()
        i.setimmediatevalue(ord(upper))

    await Timer(1, "ns")

    test_string = test_string.upper()

    result = variable_string.value
    tlog.info("After setting bytes of string value is %s" % result)
    if variable_string != test_string:
        raise TestFailure(f"{variable_string!r} {result} != '{test_string}'")


# TODO: add tests for Verilog "string_input_port" and "STRING_LOCALPARAM" (see issue #802)

@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"] or cocotb.SIM_NAME.lower().startswith(("icarus", "riviera")),
             expect_error=cocotb.result.TestFailure if cocotb.SIM_NAME.lower().startswith(("xmsim", "ncsim", "modelsim", "chronologic simulation vcs")) else ())
async def access_const_string_verilog(dut):
    """Access to a const Verilog string."""
    tlog = logging.getLogger("cocotb.test")
    string_const = dut.STRING_CONST

    await Timer(10, "ns")
    tlog.info(f"{string_const!r} is {string_const.value}")
    if not isinstance(string_const, StringObject):
        raise TestFailure("STRING_CONST was not StringObject")
    if string_const != b"TESTING_CONST":
        raise TestFailure(f"Initial value of STRING_CONST was not == b\'TESTING_CONST\' but {string_const.value} instead")

    tlog.info("Modifying const string")
    string_const <= b"MODIFIED"
    await Timer(10, "ns")
    if string_const != b"TESTING_CONST":
        raise TestFailure(f"STRING_CONST was not still b\'TESTING_CONST\' after modification but {string_const.value} instead")


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"],
             expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith("icarus") else ())
async def access_var_string_verilog(dut):
    """Access to a var Verilog string."""
    tlog = logging.getLogger("cocotb.test")
    string_var = dut.STRING_VAR

    await Timer(10, "ns")
    tlog.info(f"{string_var!r} is {string_var.value}")
    if not isinstance(string_var, StringObject):
        raise TestFailure("STRING_VAR was not StringObject")
    if string_var != b"TESTING_VAR":
        raise TestFailure(f"Initial value of STRING_VAR was not == b\'TESTING_VAR\' but {string_var.value} instead")

    tlog.info("Modifying var string")
    string_var <= b"MODIFIED"
    await Timer(10, "ns")
    if string_var != b"MODIFIED":
        raise TestFailure(f"STRING_VAR was not == b\'MODIFIED\' after modification but {string_var.value} instead")


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
async def access_constant_boolean(dut):
    """Test access to a constant boolean"""
    tlog = logging.getLogger("cocotb.test")

    constant_boolean = dut.isample_module1.EXAMPLE_BOOL
    if not isinstance(constant_boolean, ConstantObject):
        raise TestFailure("dut.stream_in_int.EXAMPLE_BOOL is not a ConstantObject")

    tlog.info("Value of %s is %d" % (constant_boolean._path, constant_boolean.value))


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
async def access_boolean(dut):
    """Test access to a boolean"""
    tlog = logging.getLogger("cocotb.test")

    boolean = dut.stream_in_bool

    return

    # if not isinstance(boolean, IntegerObject):
    #     raise TestFailure("dut.stream_in_boolean is not a IntegerObject is %s" % type(boolean))

    try:
        bit = boolean[3]
    except TestError as e:
        tlog.info("Access to bit is an error as expected")
        bitfail = True

    if not bitfail:
        raise TestFailure("Access into an integer should be invalid")

    length = len(boolean)
    if length != 1:
        raise TestFailure("Length should be 1 not %d" % length)

    tlog.info("Value of %s is %d" % (boolean._path, boolean.value))

    curr_val = int(boolean)
    output_bool = dut.stream_out_bool

    tlog.info("Before  %d After = %d" % (curr_val, (not curr_val)))

    boolean.setimmediatevalue(not curr_val)

    await Timer(1, "ns")

    tlog.info("Value of %s is now %d" % (output_bool._path, output_bool.value))
    if (int(curr_val) == int(output_bool)):
        raise TestFailure("Value did not propagate")


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def access_internal_register_array(dut):
    """Test access to an internal register array"""

    if (dut.register_array[0].value.binstr != "xxxxxxxx"):
        raise TestFailure("Failed to access internal register array value")

    dut.register_array[1].setimmediatevalue(4)

    await Timer(1, "ns")

    if (dut.register_array[1].value != 4):
        raise TestFailure("Failed to set internal register array value")


@cocotb.test(skip=True)
async def skip_a_test(dut):
    """This test shouldn't execute"""
    dut._log.info("%s = %d bits" %
                  (dut.stream_in_data._path, len(dut.stream_in_data)))
    bit = len(dut.stream_in_data) + 4
    dut.stream_in_data[bit] <= 1


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"],
             expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith("icarus") else ())
async def access_gate(dut):
    """
    Test access to a gate Object
    """
    gate = dut.test_and_gate

    if not isinstance(gate, HierarchyObject):
        raise TestFailure("Gate should be HierarchyObject")


# GHDL unable to access record types (gh-2591)
@cocotb.test(
    skip=cocotb.LANGUAGE in ["verilog"],
    expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith("ghdl") else ())
async def custom_type(dut):
    """
    Test iteration over a custom type
    """
    tlog = logging.getLogger("cocotb.test")

    new_type = dut.cosLut
    tlog.info("cosLut object {} {}".format(new_type, type(new_type)))

    expected_sub = 84
    expected_top = 4

    count = 0

    def _discover(obj):
        iter_count = 0
        for elem in obj:
            iter_count += 1
            iter_count += _discover(elem)
        return iter_count

    for sub in new_type:
        tlog.info("Sub object {} {}".format(sub, type(sub)))
        sub_count = _discover(sub)
        if sub_count != expected_sub:
            raise TestFailure("Expected %d found %d under %s" % (expected_sub, sub_count, sub))
        count += 1

    if expected_top != count:
        raise TestFailure("Expected %d found %d for cosLut" % (expected_top, count))


@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"])
async def type_check_verilog(dut):
    """
    Test if types are recognized
    """

    tlog = logging.getLogger("cocotb.test")

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
        tlog.info("Handle {}".format(handle[0]._fullname))
        if handle[0]._type != handle[1]:
            raise TestFailure("Expected {} found {} for {}".format(handle[1], handle[0]._type, handle[0]._fullname))
