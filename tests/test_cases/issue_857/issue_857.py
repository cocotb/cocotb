import cocotb
import cocotb.regression
import cocotb.triggers


@cocotb.coroutine
def test_adder(dut, val_a, val_b):
    dut.a = val_a
    dut.b = val_b
    yield cocotb.triggers.Timer(10, 'ns')
    assert dut.z == val_a + val_b


# Try to instantiate the TestFactory class using it's full specifier name.
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
test_factory = cocotb.regression.TestFactory(test_adder)
test_factory.add_option('val_a', range(16))
test_factory.add_option('val_b', range(16))
test_factory.generate_tests()