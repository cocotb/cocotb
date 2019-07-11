"""Tests for the BinaryValue type and its interaction with hardware

BinaryValue is a shim of the data stored in the simulation.
When calling .value on a signal in the DUT, it reads a binary string from the simulation
(through VPI/whichever interface is available) and places it into a BinaryValue.

These tests show the interaction between BinaryValue and the hardware, and the distinctions between
Verilog/VHDL data and Python.
"""

#TODO: Signed magnitude tests

import os

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.clock import Clock
from cocotb.result import TestError, TestSuccess
from cocotb.binary import BinaryValue, BinaryRepresentation

TEST_VHDL = os.getenv("TOPLEVEL_LANG").upper() == "VHDL"
TEST_VERILOG = os.getenv("TOPLEVEL_LANG").upper() == "VERILOG"
if not (TEST_VHDL ^ TEST_VERILOG):
    raise TestError("TOPLEVEL_LANG must be vhdl or verilog")

class BinaryTestbench:
    def __init__(self, dut):
        self.dut = dut
        self.log = dut._log

        self.clkedge = RisingEdge(self.dut.clk)

    @cocotb.coroutine
    def initialise(self):
        cocotb.fork(Clock(self.dut.clk, 1.0, units='ns').start())

        self.dut.reset <= 0
        for _ in range(2):
            yield self.clkedge
        self.dut.reset <= 1
        yield self.clkedge

def integer_endian_swap(value):
    """Swap the endian-ness of a positive integer"""
    new_value = 0
    while value > 0:
        new_value = (new_value << 1) + (value & 0x1)
        value >>= 1
    return new_value

@cocotb.test()
def test_signed_counting(dut):
    """Test behaviour of a normal counter"""
    tb = BinaryTestbench(dut)
    yield tb.initialise()

    def compare_count(expected_value, actual_value, sign_type, big_endian, desc):
        """Compare the signal with the expected count value"""
        actual_value.big_endian = big_endian
        actual_value.sign_type = sign_type

        # Shouldn't overflow so don't need to worry about the sign_type
        if not big_endian:
            if actual_value != expected_value:
                raise TestError("Values ({}) do not match. "
                                "Expected: {}; Actual: {}".format(desc,
                                                                  expected_value,
                                                                  actual_value.integer))
        else:
            expected_str = bin(expected_value)[2:].zfill(actual_value.n_bits)
            if actual_value.binstr != expected_str:
                raise TestError("Values ({}) do not match. "
                                "Expected: {}; Actual: {}".format(desc,
                                                                  expected_str,
                                                                  actual_value.binstr))

    count = 1
    for _ in range(128):
        yield tb.clkedge
        compare_count(count,
                      dut.unsigned_counter_little.value,
                      BinaryRepresentation.UNSIGNED, False,
                      "unsigned little-endian")
        compare_count(count,
                      dut.signed_counter_little.value,
                      BinaryRepresentation.TWOS_COMPLEMENT, False,
                      "signed little-endian")
        compare_count(count,
                      dut.unsigned_counter_big.value,
                      BinaryRepresentation.UNSIGNED, True,
                      "unsigned big-endian")
        compare_count(count,
                      dut.signed_counter_big.value,
                      BinaryRepresentation.TWOS_COMPLEMENT, True,
                      "signed big-endian")
        count += 1


@cocotb.test()
def test_signed_overflow(dut):
    """Test behaviour of an overflowing counter"""
    tb = BinaryTestbench(dut)
    yield tb.initialise()

    count_unsigned = BinaryValue(value=1, n_bits=3, bigEndian=False,
                                 binaryRepresentation=BinaryRepresentation.UNSIGNED)
    count_signed = BinaryValue(value=1, n_bits=4, bigEndian=False,
                               binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT)

    def compare_count(expected_value, actual_value, sign_type, big_endian, desc):
        """Compare the signal with the expected binary count value"""
        actual_value.big_endian = big_endian
        actual_value.binaryRepresentation = sign_type

        if not big_endian:
            if actual_value != expected_value:
                raise TestError("Values ({}) do not match. "
                                "Expected: {}; Actual: {}".format(desc,
                                                                  expected_value.integer,
                                                                  actual_value.integer))
        else:
            if actual_value.binstr != expected_value.binstr:
                raise TestError("Values ({}) do not match. "
                                "Expected: {}; Actual: {}".format(desc,
                                                                  expected_value.binstr,
                                                                  actual_value.binstr))

    for _ in range(128):
        yield tb.clkedge
        compare_count(count_unsigned,
                      dut.unsigned_overflow_counter_little.value,
                      BinaryRepresentation.UNSIGNED, False,
                      "unsigned little-endian")
        compare_count(count_signed,
                      dut.signed_overflow_counter_little.value,
                      BinaryRepresentation.TWOS_COMPLEMENT, False,
                      "signed little-endian")
        compare_count(count_unsigned,
                      dut.unsigned_overflow_counter_big.value,
                      BinaryRepresentation.UNSIGNED, True,
                      "unsigned big-endian")
        compare_count(count_signed,
                      dut.signed_overflow_counter_big.value,
                      BinaryRepresentation.TWOS_COMPLEMENT, True,
                      "signed big-endian")
        count_unsigned += 1
        count_signed += 1

@cocotb.test(skip=TEST_VHDL)
def test_verilog_truncation(dut):
    """Test behaviour of truncation in Verilog.

    This is using the implicit truncation in Verilog, that a user is likely
    to use, assuming it will correctly truncate the value

    However Verilog always truncates the left-most bits
    """
    tb = BinaryTestbench(dut)
    yield tb.initialise()

    def compare_truncated(long_value, short_value, sign_type, big_endian, desc):
        """Compare two equal values, one a truncation of the other"""
        short_value.big_endian = big_endian
        short_value.binaryRepresentation = sign_type
        short_length = short_value.n_bits

        truncate_value = BinaryValue(value=long_value.binstr, binaryRepresentation=sign_type,
                                     bigEndian=False, n_bits=short_length)
        truncate_value.big_endian = big_endian

        if short_value.integer != truncate_value.integer:
            raise TestError("Values ({}) do not match as expected. "
                            "Original value: {}; Truncated value: {}".format(desc,
                                                                             long_value.binstr,
                                                                             short_value.binstr))

    for _ in range(128):
        yield tb.clkedge
        compare_truncated(dut.unsigned_counter_little.value,
                          dut.truncate_unsigned_little.value,
                          BinaryRepresentation.UNSIGNED, False,
                          "unsigned little-endian")
        compare_truncated(dut.signed_counter_little.value,
                          dut.truncate_signed_little.value,
                          BinaryRepresentation.TWOS_COMPLEMENT, False,
                          "signed little-endian")
        compare_truncated(dut.unsigned_counter_big.value,
                          dut.truncate_unsigned_big.value,
                          BinaryRepresentation.UNSIGNED, True,
                          "unsigned big-endian")
        compare_truncated(dut.signed_counter_big.value,
                          dut.truncate_signed_big.value,
                          BinaryRepresentation.TWOS_COMPLEMENT, True,
                          "signed big-endian")

@cocotb.test(skip=TEST_VERILOG)
def test_vhdl_truncation(dut):
    """Test behaviour of truncation in VHDL.

    In VHDL, you cannot implicitly truncate, you must specify which bits you want.
    In the big endian case this means you can cut off the MSBs, which is what one
    would typically do in a truncation.
    """
    tb = BinaryTestbench(dut)
    yield tb.initialise()

    def create_mask(size):
        """Create a mask of 'size' bits"""
        mask = 0
        for _ in range(size):
            mask <<= 1
            mask |= 1
        return mask

    def compare_truncated(long_value, short_value, sign_type, big_endian, desc):
        """Compare two equal values, one a truncation of the other"""
        long_value.big_endian = big_endian
        short_value.big_endian = big_endian
        long_value.binaryRepresentation = sign_type
        short_value.binaryRepresentation = sign_type
        short_length = short_value.n_bits

        if sign_type == BinaryRepresentation.UNSIGNED:
            if short_value.integer != (long_value.integer & create_mask(short_length)):
                raise TestError("Values ({}) do not match as expected. "
                                "Original value: {}; Truncated value: {}".format(desc,
                                                                                 long_value.binstr,
                                                                                 short_value.binstr))
        elif sign_type == BinaryRepresentation.TWOS_COMPLEMENT:
            dut._log.info(long_value.integer)
            truncated_value = BinaryValue(value=long_value.integer, binaryRepresentation=sign_type,
                                          bigEndian=big_endian, n_bits=short_length)
            dut._log.info("{} {} {} {}".format(truncated_value.integer, truncated_value.binstr, truncated_value.n_bits, truncated_value.big_endian))
            if short_value.integer != truncated_value.integer:
                raise TestError("Values ({}) do not match as expected. "
                                "Original value: {}; Truncated value: {}".format(desc,
                                                                                 long_value.binstr,
                                                                                 truncated_value.binstr))
        else:
            raise TestError("Unrecognised sign type: {}".format(sign_type))

    for _ in range(128):
        yield tb.clkedge
        compare_truncated(dut.unsigned_counter_little.value,
                          dut.truncate_unsigned_little.value,
                          BinaryRepresentation.UNSIGNED, False,
                          "unsigned little-endian")
        compare_truncated(dut.signed_counter_little.value,
                          dut.truncate_signed_little.value,
                          BinaryRepresentation.TWOS_COMPLEMENT, False,
                          "signed little-endian")
        compare_truncated(dut.unsigned_counter_big.value,
                          dut.truncate_unsigned_big.value,
                          BinaryRepresentation.UNSIGNED, True,
                          "unsigned big-endian")
        compare_truncated(dut.signed_counter_big.value,
                          dut.truncate_signed_big.value,
                          BinaryRepresentation.TWOS_COMPLEMENT, True,
                          "signed big-endian")

@cocotb.test()
def test_extension(dut):
    """Test behaviour of sign extension"""
    tb = BinaryTestbench(dut)
    yield tb.initialise()

    def compare_extended(short_value, long_value, sign_type, big_endian, desc):
        """Compare two equal values, one an extension of the other"""
        short_value.big_endian = big_endian
        long_value.big_endian = big_endian
        short_value.binaryRepresentation = sign_type
        long_value.binaryRepresentation = sign_type
        short_length = short_value.n_bits
        long_length = long_value.n_bits

        # Verilog/VHDL have no concept of big/little endian-ness
        # Only care about left/right-most value
        if not big_endian:
            if short_value != long_value:
                raise TestError("Values ({}) do not match".format(desc))
        else:
            if sign_type == BinaryRepresentation.UNSIGNED:
                if long_value != short_value.integer * pow(2, long_value.n_bits - short_value.n_bits):
                    raise TestError("Values ({}) do not have expected equivalence".format(desc))
            # We're going to ignore the other cases (sign extension on the "wrong" side)

        if sign_type == BinaryRepresentation.UNSIGNED:
            short_to_long = '0' * (long_length - short_length) + short_value.binstr
        elif sign_type == BinaryRepresentation.TWOS_COMPLEMENT:
            short_to_long = short_value.binstr[0] * (long_length - short_length) + short_value.binstr
        else:
            raise TestError("Unsupported sign type: {}".format(sign_type))

        if short_to_long != long_value.binstr:
            raise TestError("Values ({}) do not match binstrings. "
                            "Expected: {}; Actual: {}".format(desc,
                                                              short_to_long,
                                                              long_value.binstr))

    for _ in range(128):
        yield tb.clkedge
        compare_extended(dut.unsigned_overflow_counter_little.value,
                         dut.extend_unsigned_little.value,
                         BinaryRepresentation.UNSIGNED,
                         False, "unsigned little-endian")
        compare_extended(dut.signed_overflow_counter_little.value,
                         dut.extend_signed_little.value,
                         BinaryRepresentation.TWOS_COMPLEMENT,
                         False, "signed little-endian")
        compare_extended(dut.unsigned_overflow_counter_big.value,
                         dut.extend_unsigned_big.value,
                         BinaryRepresentation.UNSIGNED,
                         True, "unsigned big-endian")
        compare_extended(dut.signed_overflow_counter_big.value,
                         dut.extend_signed_big.value,
                         BinaryRepresentation.TWOS_COMPLEMENT,
                         True, "signed big-endian")

@cocotb.test()
def test_endianness_swap(dut):
    """Test behaviour of an endian-ness swap

    Assigning big-endian value to little-endian value and vice-versa
    """
    tb = BinaryTestbench(dut)
    yield tb.initialise()

    def compare_flipped_value(big_endian_value, little_endian_value, binary_repr, desc):
        """Compare two equal values (in verilog) with different endian-ness"""
        big_endian_value.big_endian = True
        big_endian_value.binaryRepresentation = binary_repr
        little_endian_value.big_endian = False
        little_endian_value.binaryRepresentation = binary_repr

        if big_endian_value.binstr != little_endian_value.binstr:
            raise TestError("Value ({}) not matching binary strings: "
                            "bigEndian: {}; littleEndian: {}".format(desc,
                                                                     big_endian_value.binstr,
                                                                     little_endian_value.binstr))
        if big_endian_value.integer == integer_endian_swap(little_endian_value.integer): # Should never reach negative little-endian number
            raise TestError("Value ({}) should not match (flipped) integers: "
                            "bigEndian: {}; littleEndian: {}".format(desc,
                                                                     big_endian_value.integer,
                                                                     little_endian_value.integer))

    for _ in range(128):
        yield tb.clkedge
        compare_flipped_value(dut.unsigned_counter_little_to_big.value,
                              dut.unsigned_counter_little.value,
                              BinaryRepresentation.UNSIGNED,
                              "unsigned little to big")
        compare_flipped_value(dut.signed_counter_little_to_big.value,
                              dut.signed_counter_little.value,
                              BinaryRepresentation.TWOS_COMPLEMENT,
                              "signed little to big")
        compare_flipped_value(dut.unsigned_counter_big_to_little.value,
                              dut.unsigned_counter_big.value,
                              BinaryRepresentation.UNSIGNED,
                              "unsigned big to little")
        compare_flipped_value(dut.signed_counter_big_to_little.value,
                              dut.signed_counter_big.value,
                              BinaryRepresentation.TWOS_COMPLEMENT,
                              "signed big to little")

@cocotb.test(skip=TEST_VHDL)
def test_signed_function(dut):
    """Test the behaviour of the $signed Verilog function

    This forces the wire to act as signed, even if not declared as such
    Signed in Verilog is twos complement
    """
    tb = BinaryTestbench(dut)
    yield tb.initialise()

    # Expected values
    EXPECTED_SIGNED_VALUE = -57
    EXPECTED_UNSIGNED_VALUE = 199 # 11000111
    EXPECTED_STRING = "111000111"

    unsigned_little_end_signal = dut.unsigned_assigned_dollar_signed_little.value
    if unsigned_little_end_signal.binstr != EXPECTED_STRING[1:]: # Signal is only 8 bits
        raise TestError("Didn't get expected value: $signed(-57) == 11000111 (in unsigned little-endian wire)")
    unsigned_little_end_signal.big_endian = False
    unsigned_little_end_signal.binaryRepresentation = BinaryRepresentation.UNSIGNED
    if unsigned_little_end_signal.integer != EXPECTED_UNSIGNED_VALUE:
        tb.log.error("Expected value: %d; Actual value: %d",
                     EXPECTED_UNSIGNED_VALUE, unsigned_little_end_signal.integer)
        raise TestError("Didn't get expected integer value (in unsigned little-end wire)")

    unsigned_big_end_signal = dut.unsigned_assigned_dollar_signed_big.value
    if unsigned_big_end_signal.binstr != EXPECTED_STRING[1:]: # Signal is only 8 bits
        raise TestError("Didn't get expected value: $signed(-57) == 11000111 (in unsigned big-endian wire)")
    unsigned_big_end_signal.big_endian = True
    unsigned_big_end_signal.binaryRepresentation = BinaryRepresentation.UNSIGNED
    if unsigned_big_end_signal.integer != int(EXPECTED_STRING[1:][::-1], 2):
        tb.log.error("Expected value: %d; Actual value: %d",
                     int(EXPECTED_STRING[1:][::-1], 2), unsigned_big_end_signal.integer)
        raise TestError("Didn't get expected integer value (in unsigned big-end wire)")

    signed_little_end_signal = dut.signed_assigned_dollar_signed_little.value
    if signed_little_end_signal.binstr != EXPECTED_STRING:
        raise TestError("Didn't get expected value: $signed(-57) == 111000111 (in signed little-endian wire)")
    signed_little_end_signal.big_endian = False
    signed_little_end_signal.binaryRepresentation = BinaryRepresentation.TWOS_COMPLEMENT
    if signed_little_end_signal.integer != EXPECTED_SIGNED_VALUE:
        tb.log.error("Expected value: %d; Actual value: %d",
                     EXPECTED_SIGNED_VALUE, signed_little_end_signal.integer)
        raise TestError("Didn't get expected integer value (in signed little-end wire)")

    signed_big_end_signal = dut.signed_assigned_dollar_signed_big.value
    if signed_big_end_signal.binstr != EXPECTED_STRING:
        raise TestError("Didn't get expected value: $signed(-57) == 111000111 (in signed big-endian wire)")
    signed_big_end_signal.big_endian = False
    signed_big_end_signal.binaryRepresentation = BinaryRepresentation.TWOS_COMPLEMENT
    if signed_big_end_signal.integer != EXPECTED_SIGNED_VALUE: # -57 is the same value reversed when 9 bits
        tb.log.error("Expected value: %d; Actual value: %d",
                     EXPECTED_SIGNED_VALUE, signed_big_end_signal.integer)
        raise TestError("Didn't get expected integer value (in signed big-end wire)")

    raise TestSuccess("Test complete")

@cocotb.test(skip=TEST_VERILOG)
def test_to_signed_function(dut):
    """Test the behaviour of the to_signed VHDL function

    From numeric_std package.
    """
    # The behaviour here is strictly defined by the VHDL LRM
    # No implicit conversions to worry about
    tb = BinaryTestbench(dut)
    yield tb.initialise()

    # Expected values
    EXPECTED_STRING = "111000111"
    EXPECTED_VALUE = -57

    little_end_signal = dut.signed_assigned_signed_little.value
    if little_end_signal.binstr != EXPECTED_STRING:
        raise TestError("Didn't get expected value: to_signed(-57, 9) == 111000111 (for little-endian signal)")
    little_end_signal.big_endian = False
    little_end_signal.binaryRepresentation = BinaryRepresentation.TWOS_COMPLEMENT
    if little_end_signal != EXPECTED_VALUE:
        tb.log.error("Expected value: %d; Actual value: %d",
                     EXPECTED_VALUE, little_end_signal.integer)
        raise TestError("Didn't get expected integer value (for little-endian signal)")

    big_end_signal = dut.signed_assigned_signed_big.value
    if big_end_signal.binstr != EXPECTED_STRING:
        raise TestError("Didn't get expected value: to_signed(-57, 9) == 111000111 (for big-endian signal)")
    big_end_signal.big_endian = True
    big_end_signal.binaryRepresentation = BinaryRepresentation.TWOS_COMPLEMENT
    if big_end_signal.integer != EXPECTED_VALUE: # Fun: -57 is the same backwards when 9 bits
        tb.log.error("Expected value: %d; Actual value: %d",
                     EXPECTED_VALUE, big_end_signal.integer)
        raise TestError("Didn't get expected integer value (in big-endian signal)")

    raise TestSuccess("Test complete")
