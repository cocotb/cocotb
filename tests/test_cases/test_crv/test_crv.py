
import cocotb
import unittest
import crv_unittest
from cocotb.triggers import Timer

@cocotb.test()
def test_crv(dut):
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromModule(crv_unittest))
    unittest.TextTestRunner().run(suite)
    yield Timer(10)
