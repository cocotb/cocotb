import cocotb
from cocotb.binary import BinaryValue, BinaryRepresentation
from cocotb.triggers import Timer
import logging

import random

@cocotb.test()
def issue_608(dut):
    """ BinaryValues test """
    
    tlog = logging.getLogger("cocotb.test")
    yield Timer(10)

    def test_bin(value, bitW, bigEndian = True):
        tlog.info("Testing value \"%d\" using %d bits in %s ..." % 
          (value, bitW, "big endian" if bigEndian else "little endian")
        )
        v = BinaryValue(value, bitW, bigEndian)
        tlog.info("Binary representation: %s" % v.binstr)
        assert (v == value)

    test_bin(3,3)
    test_bin(4,4)
    test_bin(4,3)
    test_bin(5,5)
    test_bin(11,4) #something assymetric
    test_bin(3,3, False)
    test_bin(4,4, False)
    test_bin(4,3, False)
    test_bin(5,5, False)
    test_bin(11,4, False)

    for _ in range(100):
        bw = random.randint(1,16)
        value = random.randint(0,2**bw-1)
        endian = random.choice([True, False])
        test_bin(value,bw,endian)
    
    
