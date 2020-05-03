import cocotb
from cocotb.triggers import Timer


@cocotb.coroutine
def coroutine_with_undef():
    new_variable = undefined_variable  # noqa
    yield Timer(1, units='ns')


@cocotb.test(expect_error=True)
def fork_erroring_coroutine(dut):
    cocotb.fork(coroutine_with_undef())
    yield Timer(10, units='ns')
