import cocotb
from cocotb.triggers import Timer


async def coroutine_with_undef():
    new_variable = undefined_variable  # noqa


@cocotb.test(expect_error=NameError)
async def fork_erroring_coroutine(dut):
    cocotb.fork(coroutine_with_undef())
    await Timer(10, units='ns')
