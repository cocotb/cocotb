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
import os
import textwrap
from cocotb.triggers import Timer
from cocotb.result import TestError, TestFailure
from cocotb.handle import IntegerObject, ConstantObject, HierarchyObject, StringObject


@cocotb.test()
def recursive_discover(dut):
    """Discover absolutely everything in the DUT"""
    yield Timer(0)
    def _discover(obj):
        for thing in obj:
            dut._log.info("Found %s (%s)", thing._name, type(thing))
            _discover(thing)
    _discover(dut)

@cocotb.test()
def discover_module_values(dut):
    """Discover everything in the DUT"""
    yield Timer(0)
    count = 0
    for thing in dut:
        thing._log.info("Found something: %s" % thing._fullname)
        count += 1
    if count < 2:
        raise TestFailure("Expected to discover things in the DUT")

@cocotb.test(skip=True)
def ipython_embed(dut):
    yield Timer(0)
    import IPython
    IPython.embed()


@cocotb.test(skip=True)
def ipython_embed_kernel(dut):
    """Start an interactive Python shell."""
    yield Timer(0)
    import IPython
    print(textwrap.dedent("""
    ###############################################################################
    Running IPython embed_kernel()

    You can now send this process into the background with "Ctrl-Z bg" and run
        jupyter console --existing
    or
        jupyter qtconsole --existing
    or
        jupyter console --existing kernel-{}.json
    ###############################################################################""".format(os.getpid())))
    IPython.embed_kernel()

    
@cocotb.test(expect_error=True)
def discover_value_not_in_dut(dut):
    """Try and get a value from the DUT that is not there"""
    yield Timer(0)
    fake_signal = dut.fake_signal
    yield Timer(0)


@cocotb.test()
def access_signal(dut):
    """Access a signal using the assignment mechanism"""
    tlog = logging.getLogger("cocotb.test")
    signal = dut.stream_in_data

    tlog.info("Signal is %s" % type(signal))
    dut.stream_in_data.setimmediatevalue(1)
    yield Timer(10)
    if dut.stream_in_data.value.integer != 1:
        raise TestError("%s.%s != %d" %
                        (str(dut.stream_in_data),
                         dut.stream_in_data.value.integer, 1))


@cocotb.test(expect_error=cocotb.SIM_NAME in ["Icarus Verilog"],
             skip=cocotb.LANGUAGE in ["vhdl"])
def access_single_bit(dut):
    """
    Access a single bit in a vector of the DUT

    Icarus v0.96 doesn't support single bit access to vectors
    """
    dut.stream_in_data <= 0
    yield Timer(10)
    dut._log.info("%s = %d bits" %
                 (str(dut.stream_in_data), len(dut.stream_in_data)))
    dut.stream_in_data[2] <= 1
    yield Timer(10)
    if dut.stream_out_data_comb.value.integer != (1<<2):
        raise TestError("%s.%s != %d" %
                        (str(dut.stream_out_data_comb),
                         dut.stream_out_data_comb.value.integer, (1<<2)))


@cocotb.test(expect_error=cocotb.SIM_NAME in ["Icarus Verilog"],
             skip=cocotb.LANGUAGE in ["vhdl"])
def access_single_bit_assignment(dut):
    """
    Access a single bit in a vector of the DUT using the assignment mechanism

    Icarus v0.96 doesn't support single bit access to vectors
    """
    dut.stream_in_data = 0
    yield Timer(10)
    dut._log.info("%s = %d bits" %
                 (str(dut.stream_in_data), len(dut.stream_in_data)))
    dut.stream_in_data[2] = 1
    yield Timer(10)
    if dut.stream_out_data_comb.value.integer != (1<<2):
        raise TestError("%s.%s != %d" %
                        (str(dut.stream_out_data_comb),
                         dut.stream_out_data_comb.value.integer, (1<<2)))


@cocotb.test(expect_error=True)
def access_single_bit_erroneous(dut):
    """Access a non-existent single bit"""
    yield Timer(10)
    dut._log.info("%s = %d bits" %
                 (str(dut.stream_in_data), len(dut.stream_in_data)))
    bit = len(dut.stream_in_data) + 4
    dut.stream_in_data[bit] <= 1
    yield Timer(10)

@cocotb.test(expect_error=cocotb.SIM_NAME.lower().startswith(("icarus")),
             expect_fail=cocotb.SIM_NAME.lower().startswith(("riviera")) and cocotb.LANGUAGE in ["verilog"])
def access_integer(dut):
    """Integer should show as an IntegerObject"""
    bitfail = False
    tlog = logging.getLogger("cocotb.test")
    yield Timer(10)
    test_int = dut.stream_in_int
    if not isinstance(test_int, IntegerObject):
        raise TestFailure("dut.stream_in_int is not an integer")

    try:
        bit = test_int[3]
    except IndexError as e:
        tlog.info("Access to bit is an error as expected")
        bitFail = True

    if not bitFail:
        raise TestFailure("Access into an integer should be invalid")

    length = len(test_int)
    if length is not 1:
        raise TestFailure("Length should be 1 not %d" % length)

@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
def access_ulogic(dut):
    """Access a std_ulogic as enum"""
    tlog = logging.getLogger("cocotb.test")
    yield Timer(10)
    constant_integer = dut.stream_in_valid


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
def access_constant_integer(dut):
    """
    Access a constant integer
    """
    tlog = logging.getLogger("cocotb.test")
    yield Timer(10)
    constant_integer = dut.isample_module1.EXAMPLE_WIDTH
    tlog.info("Value of EXAMPLE_WIDTH is %d" % constant_integer)
    if not isinstance(constant_integer, ConstantObject):
        raise TestFailure("EXAMPLE_WIDTH was not constant")
    if constant_integer != 7:
        raise TestFailure("EXAMPLE_WIDTH was not 7")

@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
def access_string_vhdl(dut):
    """Access to a string, both constant and signal."""
    tlog = logging.getLogger("cocotb.test")
    yield Timer(10)
    constant_string = dut.isample_module1.EXAMPLE_STRING;
    tlog.info("%r is %s" % (constant_string, str(constant_string)))
    if not isinstance(constant_string, ConstantObject):
        raise TestFailure("EXAMPLE_STRING was not constant")
    if constant_string != "TESTING":
        raise TestFailure("EXAMPLE_STRING was not == \'TESTING\'")

    tlog.info("Test writing under size")

    test_string = "cocotb"
    dut.stream_in_string.setimmediatevalue(test_string)

    variable_string = dut.stream_out_string
    if variable_string != '':
        raise TestFailure("%r not \'\'" % variable_string)

    yield Timer(10)

    if variable_string != test_string:
        raise TestFailure("%r %s != '%s'" % (variable_string, str(variable_string), test_string))

    test_string = "longer_than_the_array"
    tlog.info("Test writing over size with '%s'" % test_string)

    dut.stream_in_string.setimmediatevalue(test_string)
    variable_string = dut.stream_out_string

    yield Timer(10)

    test_string = test_string[:len(variable_string)]

    if variable_string != test_string:
        raise TestFailure("%r %s != '%s'" % (variable_string, str(variable_string), test_string))

    tlog.info("Test read access to a string character")

    yield Timer(10)

    idx = 3

    result_slice = variable_string[idx]

    # String is defined as string(1 to 8) so idx=3 will access the 3rd character
    if chr(result_slice) != test_string[idx-1]:
        raise TestFailure("Single character did not match '%c' != '%c'" %
                          (result_slice, test_string[idx]))

    tlog.info("Test write access to a string character")

    yield Timer(10)

    for i in variable_string:
        lower = chr(i)
        upper = lower.upper()
        i.setimmediatevalue(ord(upper))

    yield Timer(10)

    test_string = test_string.upper()

    result = str(variable_string);
    tlog.info("After setting bytes of string value is %s" % result)
    if variable_string != test_string:
        raise TestFailure("%r %s != '%s'" % (variable_string, result, test_string))


# TODO: add tests for Verilog "string_input_port" and "STRING_LOCALPARAM" (see issue #802)

@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"],
             expect_error=cocotb.SIM_NAME.lower().startswith("icarus"))
def access_const_string_verilog(dut):
    """Access to a const Verilog string."""
    tlog = logging.getLogger("cocotb.test")

    yield Timer(10)
    string_const = dut.STRING_CONST;
    tlog.info("%r is %s" % (string_const, str(string_const)))
    if not isinstance(string_const, StringObject):
        raise TestFailure("STRING_CONST was not StringObject")
    if string_const != "TESTING_CONST":
        raise TestFailure("STRING_CONST was not == \'TESTING_CONST\'")
    
    tlog.info("Modifying const string")
    string_const <= "MODIFIED"
    yield Timer(10)
    string_const = dut.STRING_CONST;
    if string_const != "TESTING_CONST":
        raise TestFailure("STRING_CONST was not still \'TESTING_CONST\'")

    
@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"],
             expect_error=cocotb.SIM_NAME.lower().startswith("icarus"))
def access_var_string_verilog(dut):
    """Access to a var Verilog string."""
    tlog = logging.getLogger("cocotb.test")

    yield Timer(10)
    string_var = dut.STRING_VAR;
    tlog.info("%r is %s" % (string_var, str(string_var)))
    if not isinstance(string_var, StringObject):
        raise TestFailure("STRING_VAR was not StringObject")
    if string_var != "TESTING_VAR":
        raise TestFailure("STRING_VAR was not == \'TESTING_VAR\'")
    
    tlog.info("Modifying var string")
    string_var <= "MODIFIED"
    yield Timer(10)
    string_var = dut.STRING_VAR;
    if string_var != "MODIFIED":
        raise TestFailure("STRING_VAR was not == \'MODIFIED\'")


@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
def access_constant_boolean(dut):
    """Test access to a constant boolean"""
    tlog = logging.getLogger("cocotb.test")

    yield Timer(10)
    constant_boolean = dut.isample_module1.EXAMPLE_BOOL
    if not isinstance(constant_boolean, ConstantObject):
        raise TestFailure("dut.stream_in_int.EXAMPLE_BOOL is not a ConstantObject")

    tlog.info("Value of %s is %d" % (constant_boolean, constant_boolean))

@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
def access_boolean(dut):
    """Test access to a boolean"""
    tlog = logging.getLogger("cocotb.test")

    yield Timer(10)
    boolean = dut.stream_in_bool

    return

    #if not isinstance(boolean, IntegerObject):
    #    raise TestFailure("dut.stream_in_boolean is not a IntegerObject is %s" % type(boolean))

    try:
        bit = boolean[3]
    except TestError as e:
        tlog.info("Access to bit is an error as expected")
        bitFail = True

    if not bitFail:
        raise TestFailure("Access into an integer should be invalid")

    length = len(boolean)
    if length is not 1:
        raise TestFailure("Length should be 1 not %d" % length)

    tlog.info("Value of %s is %d" % (boolean, boolean))

    curr_val = int(boolean)
    output_bool = dut.stream_out_bool

    tlog.info("Before  %d After = %d" % (curr_val, (not curr_val)))

    boolean.setimmediatevalue(not curr_val)

    yield Timer(1)

    tlog.info("Value of %s is now %d" % (output_bool, output_bool))
    if (int(curr_val) == int(output_bool)):
        raise TestFailure("Value did not propogate")

@cocotb.test()
def access_internal_register_array(dut):
    """Test access to an internal register array"""

    if (dut.register_array[0].value.binstr != "xxxxxxxx"):
        raise TestFailure("Failed to access internal register array value")

    dut.register_array[1].setimmediatevalue(4)
    
    yield Timer(1)

    if (dut.register_array[1].value != 4):
        raise TestFailure("Failed to set internal register array value")

@cocotb.test(skip=True)
def skip_a_test(dut):
    """This test shouldn't execute"""
    yield Timer(10)
    dut._log.info("%s = %d bits" %
                 (str(dut.stream_in_data), len(dut.stream_in_data)))
    bit = len(dut.stream_in_data) + 4
    dut.stream_in_data[bit] <= 1
    yield Timer(10)

@cocotb.test(skip=cocotb.LANGUAGE in ["vhdl"],
             expect_error=cocotb.SIM_NAME.lower().startswith(("icarus")))
def access_gate(dut):
    """
    Test access to a gate Object
    """
    tlog = logging.getLogger("cocotb.test")

    yield Timer(10)

    gate = dut.test_and_gate

    if not isinstance(gate, HierarchyObject):
        raise TestFailure("Gate should be HierarchyObject")

@cocotb.test(skip=cocotb.LANGUAGE in ["verilog"])
def custom_type(dut):
    """
    Test iteration over a custom type
    """
    tlog = logging.getLogger("cocotb.test")

    yield Timer(10)

    new_type = dut.cosLut
    tlog.info("cosLut object %s %s" % (new_type, type(new_type)))

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
        tlog.info("Sub object %s %s" % (sub, type(sub)))
        sub_count = _discover(sub)
        if sub_count != expected_sub:
            raise TestFailure("Expected %d found %d under %s" % (expected_sub, sub_count, sub))
        count += 1

    if expected_top != count:
        raise TestFailure("Expected %d found %d for cosLut" % (expected_top, count))

