import cocotb
import cocotb.regression
import cocotb.triggers


async def dummy_coroutine(dut):
    await cocotb.triggers.Timer(10, "ns")


# Try to instantiate the TestFactory class using its full specifier name.
#
# In issue #857, a global variable named "regression" in the cocotb module hide
# the module cocotb.regression, so the TestFactory class is not accessible with
# an import like
#
# >>> import cocotb.regression
# >>> factory = cocotb.regression.FactoryManager()
#
# The class is still accessible by an import like
#
# >>> from cocotb.regression import TestFactory
# >>> factory = TestFactory()
#
# but the discoverer of the bug prefers the former approach.
#
# And in general, it's probably a good idea to not have name conflicts ;)
test_factory = cocotb.regression.TestFactory(dummy_coroutine)
test_factory.generate_tests()
