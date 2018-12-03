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
    
    #example from BinaryValue class
    vec = BinaryValue()
    vec.integer = 42
    tlog.info("\"42\" in binary is %s, value is %d" % (vec.binstr, vec))

    def test_bin(value, bitW, bigEndian = True, binRepr = BinaryRepresentation.UNSIGNED):
        tlog.info("Testing value \"%d\" using %d bits in %s in %s representation..." % 
          (value, bitW, "big endian" if bigEndian else "little endian", 
           "unsigned" if binRepr == BinaryRepresentation.UNSIGNED else 
           "two's complement" if binRepr == BinaryRepresentation.TWOS_COMPLEMENT else
           "signed magnitude")
        )
        
        v = BinaryValue(value, bitW, bigEndian, binRepr)

        tlog.info("...integer representation (BinaryValue.integer): %s" % v.integer)
        tlog.info("...binary representation (BinaryValue.binstr): %s" % v.binstr)
        tlog.info("...LSB (BinaryValue[0]): %s" % v[0])
        tlog.info("...MSB (BinaryValue[%d]): %s" % (bitW-1, v.binstr[bitW-1]))
        
        #assert (v[0] == value%2) #check LSB
        assert (v == value == v.integer) #check BinaryValue value vs originally assigned one

    test_bin(42,6)
    test_bin(3,3)
    test_bin(4,4)
    test_bin(4,3)
    test_bin(-5,6, binRepr = BinaryRepresentation.TWOS_COMPLEMENT)
    test_bin(5,6, binRepr = BinaryRepresentation.TWOS_COMPLEMENT)
    test_bin(-5,6, binRepr = BinaryRepresentation.SIGNED_MAGNITUDE)
    test_bin(5,6, binRepr = BinaryRepresentation.SIGNED_MAGNITUDE)

    for _ in range(100):
        bw = random.randint(2,64)
        binRepr = random.choice(
          [BinaryRepresentation.UNSIGNED, 
           BinaryRepresentation.SIGNED_MAGNITUDE, 
           BinaryRepresentation.TWOS_COMPLEMENT]
        )
        if (binRepr == BinaryRepresentation.UNSIGNED):
            value = random.randint(0,2**bw-1)
        elif (binRepr == BinaryRepresentation.TWOS_COMPLEMENT):
            value = random.randint(-(2**(bw-1)),2**(bw-1)-1)
        else:
            value = random.randint(-(2**(bw-1)-1),2**(bw-1)-1)
            
        #bigEndian = random.choice([True, False])
        bigEndian = True #currently only bigEndian works
        
        test_bin(value,bw,bigEndian,binRepr)
    
    
