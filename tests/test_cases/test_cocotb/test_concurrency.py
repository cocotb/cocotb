import cocotb


class ExampleException(Exception):
    """Used by a few tests"""


async def test_concurrency_types(func):

    async def coro():
        return 1

    func(coro()).kill()

    @cocotb.coroutine
    def old_coro():
        yield cocotb.triggers.NullTrigger()
        return 1

    func(coro()).kill()

    # accidental async generator test in test_async_generators.py

    def whoops_no_decorator():
        yield cocotb.triggers.NullTrigger()
        return 1

    try:
        func(whoops_no_decorator())
    except TypeError as e:
        assert "@cocotb.coroutine" in str(e)

    try:
        func(old_coro)  # unstarted decorated coroutine
    except TypeError as e:
        assert "forget to call" in str(e)


@cocotb.test()
async def test_run_task_types(dut):
    await test_concurrency_types(cocotb.run_task)


@cocotb.test()
async def test_fire_and_forget_types(dut):
    await test_concurrency_types(cocotb.fire_and_forget)


@cocotb.test()
async def test_fork_types(dut):
    await test_concurrency_types(cocotb.fork)


@cocotb.test()
async def test_run_task_value(dut):

    async def example():
        await cocotb.triggers.Timer(10, 'ns')
        return 42

    future = cocotb.run_task(example())
    await cocotb.triggers.Timer(1, 'ns')
    res = await future
    assert res == 42


@cocotb.test()
async def test_run_task_exception(dut):

    async def example():
        await cocotb.triggers.Timer(10, 'ns')
        raise ExampleException

    future = cocotb.run_task(example())
    await cocotb.triggers.Timer(1, 'ns')
    try:
        await future
    except ExampleException:
        pass
    else:
        assert False, "should have thrown"


@cocotb.test(expect_error=ExampleException)
async def test_fire_and_forget_exception(dut):

    async def example():
        await cocotb.triggers.Timer(1, 'ns')
        raise ExampleException

    cocotb.fire_and_forget(example())

    await cocotb.triggers.Timer(10, 'ns')


@cocotb.test()
async def test_fire_and_forget_exception_cancelled(dut):

    async def example():
        await cocotb.triggers.Timer(2, 'ns')
        raise ExampleException

    thread = cocotb.fire_and_forget(example())

    await cocotb.triggers.Timer(1, 'ns')
    thread.kill()
    await cocotb.triggers.Timer(2, 'ns')
