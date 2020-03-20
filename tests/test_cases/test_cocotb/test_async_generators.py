import cocotb


async def whoops_async_generator():
    # the user should have used `await` here, but they wrote `yield` by accident.
    yield cocotb.triggers.Timer(1)


@cocotb.test()
def test_yielding_accidental_async_generator(dut):
    # this test deliberately does not use `async def`, as we are testing the behavior of `yield`
    try:
        yield whoops_async_generator()
    except TypeError as e:
        assert "async generator" in str(e)
    else:
        assert False, "should have thrown"


@cocotb.test()
async def test_forking_accidental_async_generator(dut):
    try:
        cocotb.fork(whoops_async_generator())
    except TypeError as e:
        assert "async generator" in str(e)
    else:
        assert False, "should have thrown"


@cocotb.coroutine
async def whoops_async_generator_decorated():
    yield cocotb.triggers.Timer(1)


@cocotb.test()
async def test_decorating_accidental_async_generator(dut):
    try:
        await whoops_async_generator_decorated()
    except TypeError as e:
        assert "async generator" in str(e)
    else:
        assert False, "should have thrown"
