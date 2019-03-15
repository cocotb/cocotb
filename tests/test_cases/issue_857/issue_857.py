import cocotb
from cocotb import triggers, result
import cocotb.regression
import types


@cocotb.test()
def issue_857(dut):
    """ cocotb.regression must be a module """
    if not isinstance(cocotb.regression, types.ModuleType):
        yield result.TestFailure("cocotb.regression is not a module")
