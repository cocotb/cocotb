"""Test case for BinaryValue behaviour documented in issue #608

https://github.com/potentialventures/cocotb/issues/608
"""
import logging
import random

import cocotb
from cocotb.binary import BinaryValue
from cocotb.triggers import Timer

@cocotb.test()
def issue_608(dut):
    """BinaryValues test"""

    tlog = logging.getLogger("cocotb.test")
    yield Timer(10)

    def test_bin(value, bitW, bigEndian=True):
        """Test for a single binary value"""
        tlog.info("Testing value \"%d\" using %d bits in %s ...",
                  value, bitW,
                  "big endian" if bigEndian else "little endian")
        bin_value = BinaryValue(value, bitW, bigEndian)
        tlog.info("Binary representation: %s", bin_value.binstr)
        assert bin_value == value

    test_bin(3, 3)
    test_bin(4, 4)
    test_bin(4, 3)
    test_bin(5, 5)
    test_bin(11, 4)  # something asymmetric
    test_bin(3, 3, False)
    test_bin(4, 4, False)
    test_bin(4, 3, False)
    test_bin(5, 5, False)
    test_bin(11, 4, False)

    for _ in range(100):
        bit_width = random.randint(1, 16)
        value = random.randint(0, 2 ** bit_width - 1)
        endian = random.choice([True, False])
        test_bin(value, bit_width, endian)
