# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Test for scheduler and coroutine behavior

* fork
* join
* kill
"""
import logging
import re

import cocotb
from cocotb.triggers import Join, Timer, RisingEdge, Trigger, NullTrigger, Combine, Event, ReadOnly, First
from cocotb.clock import Clock
from common import clock_gen


test_flag = False


async def clock_yield(generator):
    global test_flag
    await Join(generator)
    test_flag = True


@cocotb.test()
async def test_coroutine_kill(dut):
    """Test that killing a coroutine causes pending routine continue"""
    global test_flag
    clk_gen = cocotb.scheduler.add(clock_gen(dut.clk))
    await Timer(100, "ns")
    clk_gen_two = cocotb.fork(clock_yield(clk_gen))
    await Timer(100, "ns")
    clk_gen.kill()
    assert not test_flag
    await Timer(1000, "ns")
    assert test_flag


async def clock_one(dut):
    count = 0
    while count != 50:
        await RisingEdge(dut.clk)
        await Timer(1000, "ns")
        count += 1


async def clock_two(dut):
    count = 0
    while count != 50:
        await RisingEdge(dut.clk)
        await Timer(10_000, "ns")
        count += 1


@cocotb.test()
async def test_coroutine_close_down(dut):
    log = logging.getLogger("cocotb.test")
    clk_gen = cocotb.fork(Clock(dut.clk, 100, "ns").start())

    coro_one = cocotb.fork(clock_one(dut))
    coro_two = cocotb.fork(clock_two(dut))

    await Join(coro_one)
    await Join(coro_two)

    log.info("Back from joins")


@cocotb.test()
async def join_finished(dut):
    """
    Test that joining a coroutine that has already been joined gives
    the same result as it did the first time.
    """

    retval = None

    async def some_coro():
        await Timer(1, "ns")
        return retval

    coro = cocotb.fork(some_coro())

    retval = 1
    x = await coro.join()
    assert x == 1

    # joining the second time should give the same result.
    # we change retval here to prove it does not run again
    retval = 2
    x = await coro.join()
    assert x == 1


@cocotb.test()
async def consistent_join(dut):
    """
    Test that joining a coroutine returns the finished value
    """
    async def wait_for(clk, cycles):
        rising_edge = RisingEdge(clk)
        for _ in range(cycles):
            await rising_edge
        return 3

    cocotb.fork(Clock(dut.clk, 2000, 'ps').start())

    short_wait = cocotb.fork(wait_for(dut.clk, 10))
    long_wait = cocotb.fork(wait_for(dut.clk, 30))

    await wait_for(dut.clk, 20)
    a = await short_wait.join()
    b = await long_wait.join()
    assert a == b == 3


@cocotb.test()
async def test_kill_twice(dut):
    """
    Test that killing a coroutine that has already been killed does not crash
    """
    clk_gen = cocotb.fork(Clock(dut.clk, 100, "ns").start())
    await Timer(1, "ns")
    clk_gen.kill()
    await Timer(1, "ns")
    clk_gen.kill()


@cocotb.test()
async def test_join_identity(dut):
    """
    Test that Join() returns the same object each time
    """
    clk_gen = cocotb.fork(Clock(dut.clk, 100, "ns").start())

    assert Join(clk_gen) is Join(clk_gen)
    await Timer(1, "ns")
    clk_gen.kill()


@cocotb.test()
async def test_trigger_with_failing_prime(dut):
    """ Test that a trigger failing to prime throws """
    class ABadTrigger(Trigger):
        def prime(self, callback):
            raise RuntimeError("oops")

    await Timer(1, "ns")
    try:
        await ABadTrigger()
    except RuntimeError as exc:
        assert "oops" in str(exc)
    else:
        assert False


@cocotb.test()
async def test_stack_overflow(dut):
    """
    Test against stack overflows when starting many coroutines that terminate
    before passing control to the simulator.
    """
    # gh-637
    async def null_coroutine():
        await NullTrigger()

    for _ in range(10_000):
        await null_coroutine()

    await Timer(100, "ns")


@cocotb.test()
async def test_stack_overflow_pending_coros(dut):
    """
    Test against stack overflow when queueing many pending coroutines
    before yielding to scheduler.
    """
    # gh-2489
    async def simple_coroutine():
        await Timer(10, "step")

    coros = [cocotb.scheduler.start_soon(simple_coroutine()) for _ in range(1024)]

    await Combine(*coros)


@cocotb.test()
async def test_kill_coroutine_waiting_on_the_same_trigger(dut):
    # gh-1348
    # NOTE: this test depends on scheduling priority.
    # It assumes that the first task to wait on a trigger will be woken first.
    # The fix for gh-1348 should prevent that from mattering.
    dut.clk.setimmediatevalue(0)

    victim_resumed = False

    async def victim():
        await Timer(1, "step")  # prevent scheduling of RisingEdge before killer
        await RisingEdge(dut.clk)
        nonlocal victim_resumed
        victim_resumed = True
    victim_task = cocotb.fork(victim())

    async def killer():
        await RisingEdge(dut.clk)
        victim_task.kill()
    cocotb.fork(killer())

    await Timer(2, "step")  # allow Timer in victim to pass making it schedule RisingEdge after the killer
    dut.clk <= 1
    await Timer(1, "step")
    assert not victim_resumed


@cocotb.test()
async def test_nulltrigger_reschedule(dut):
    """
    Test that NullTrigger doesn't immediately reschedule the waiting coroutine.

    The NullTrigger will be added to the end of the list of pending triggers.
    """
    log = logging.getLogger("cocotb.test")
    last_fork = None

    @cocotb.coroutine   # TODO: Remove once Combine accepts bare coroutines
    async def reschedule(n):
        nonlocal last_fork
        for i in range(4):
            log.info(f"Fork {n}, iteration {i}, last fork was {last_fork}")
            assert last_fork != n
            last_fork = n
            await NullTrigger()

    # Test should start in event loop
    await Combine(*(reschedule(i) for i in range(4)))

    await Timer(1, "ns")

    # Event loop when simulator returns
    await Combine(*(reschedule(i) for i in range(4)))


@cocotb.test()
async def test_event_set_schedule(dut):
    """
    Test that Event.set() doesn't cause an immediate reschedule.

    The coroutine waiting with Event.wait() will be woken after
    the current coroutine awaits a trigger.
    """

    e = Event()
    waiter_scheduled = False

    async def waiter(event):
        await event.wait()
        nonlocal waiter_scheduled
        waiter_scheduled = True

    cocotb.fork(waiter(e))

    e.set()

    # waiter() shouldn't run until after test awaits a trigger
    assert waiter_scheduled is False

    await NullTrigger()

    assert waiter_scheduled is True


@cocotb.test()
async def test_last_scheduled_write_wins(dut):
    """
    Test that the last scheduled write for a signal handle is the value that is written.
    """
    log = logging.getLogger("cocotb.test")
    e = Event()
    dut.stream_in_data.setimmediatevalue(0)

    @cocotb.coroutine   # TODO: Remove once Combine accepts bare coroutines
    async def first():
        await Timer(1, "ns")
        log.info("scheduling stream_in_data <= 1")
        dut.stream_in_data <= 1
        e.set()

    @cocotb.coroutine   # TODO: Remove once Combine accepts bare coroutines
    async def second():
        await Timer(1, "ns")
        await e.wait()
        log.info("scheduling stream_in_data <= 2")
        dut.stream_in_data <= 2

    await Combine(first(), second())

    await ReadOnly()

    assert dut.stream_in_data.value.integer == 2

    await Timer(1, "ns")
    dut.array_7_downto_4 <= [1, 2, 3, 4]
    dut.array_7_downto_4[7] <= 10

    await ReadOnly()

    assert dut.array_7_downto_4.value == [10, 2, 3, 4]


@cocotb.test()
async def test_task_repr(dut):
    """Test RunningTask.__repr__."""
    log = logging.getLogger("cocotb.test")
    gen_e = Event('generator_coro_inner')

    def generator_coro_inner():
        gen_e.set()
        yield Timer(1, units='ns')
        raise ValueError("inner")

    @cocotb.coroutine   # testing debug with legacy coroutine syntax
    def generator_coro_outer():
        yield from generator_coro_inner()

    gen_task = generator_coro_outer()

    log.info(repr(gen_task))
    assert re.match(r"<Task \d+ created coro=generator_coro_outer\(\)>", repr(gen_task))

    cocotb.fork(gen_task)

    await gen_e.wait()

    log.info(repr(gen_task))
    assert re.match(r"<Task \d+ pending coro=generator_coro_inner\(\) trigger=<Timer of 1000.00ps at \w+>>", repr(gen_task))

    try:
        await Join(gen_task)
    except ValueError:
        pass

    log.info(repr(gen_task))
    assert re.match(r"<Task \d+ finished coro=generator_coro_outer\(\) outcome=Error\(ValueError\('inner',?\)\)>", repr(gen_task))

    coro_e = Event('coroutine_inner')

    async def coroutine_forked(task):
        log.info(repr(task))
        assert re.match(r"<Task \d+ adding coro=coroutine_outer\(\)>", repr(task))

    @cocotb.coroutine   # Combine requires use of cocotb.coroutine
    async def coroutine_wait():
        await Timer(1, units='ns')

    async def coroutine_inner():
        await coro_e.wait()
        this_task = coro_e.data
        # cr_await is None while the coroutine is running, so we can't get the stack...
        log.info(repr(this_task))
        assert re.match(r"<Task \d+ running coro=coroutine_outer\(\)>", repr(this_task))

        cocotb.fork(coroutine_forked(this_task))
        await Combine(*(coroutine_wait() for _ in range(2)))

        return "Combine done"

    async def coroutine_middle():
        return await coroutine_inner()

    async def coroutine_outer():
        return await coroutine_middle()

    coro_task = cocotb.fork(coroutine_outer())

    coro_e.set(coro_task)

    await NullTrigger()

    log.info(repr(coro_task))
    assert re.match(
        r"<Task \d+ pending coro=coroutine_inner\(\) trigger=Combine\(Join\(<Task \d+>\), Join\(<Task \d+>\)\)>",
        repr(coro_task)
    )

    await Timer(2, units='ns')

    log.info(repr(coro_task))
    assert re.match(r"<Task \d+ finished coro=coroutine_outer\(\) outcome=Value\('Combine done'\)", repr(coro_task))

    async def coroutine_first():
        await First(coroutine_wait(), Timer(2, units='ns'))

    coro_task = cocotb.fork(coroutine_first())

    log.info(repr(coro_task))
    assert re.match(
        r"<Task \d+ pending coro=coroutine_first\(\) trigger=First\(Join\(<Task \d+>\), <Timer of 2000.00ps at \w+>\)>",
        repr(coro_task)
    )

    async def coroutine_timer():
        await Timer(1, units='ns')

    coro_task = cocotb.fork(coroutine_timer())

    # Trigger.__await__ should be popped from the coroutine stack
    log.info(repr(coro_task))
    assert re.match(r"<Task \d+ pending coro=coroutine_timer\(\) trigger=<Timer of 1000.00ps at \w+>>", repr(coro_task))


@cocotb.test()
async def test_start_soon_async(_):
    """ Tests start_soon works with coroutines """
    a = 0

    async def example():
        nonlocal a
        a = 1

    cocotb.scheduler.start_soon(example())
    assert a == 0
    await NullTrigger()
    assert a == 1


@cocotb.test()
async def test_start_soon_decorator(_):
    """ Tests start_soon works with RunningTasks """
    a = 0

    async def example():
        nonlocal a
        a = 1

    cocotb.scheduler.start_soon(example())
    assert a == 0
    await NullTrigger()
    assert a == 1


@cocotb.test()
async def test_start_soon_scheduling(dut):
    """Test order of scheduling when using start_soon."""
    coro_scheduled = False

    def react_wrapper(trigger):
        """Function to prime trigger with."""
        log = logging.getLogger("cocotb.test")
        log.debug("react_wrapper start")
        assert coro_scheduled is False
        cocotb.scheduler._react(trigger)
        assert coro_scheduled is True
        log.debug("react_wrapper end")

    async def coro():
        nonlocal coro_scheduled
        coro_scheduled = True

    t = Timer(1, 'step')
    # pre-prime with wrapper function instead of letting scheduler prime it normally
    t.prime(react_wrapper)
    await t
    cocotb.scheduler.start_soon(coro())
    await Timer(1, 'step')  # await a GPITrigger to ensure control returns to simulator
    assert coro_scheduled is True


@cocotb.test()
async def test_await_start_soon(_):
    """Test awaiting start_soon queued coroutine before it starts."""
    async def coro():
        start_time = cocotb.utils.get_sim_time(units="ns")
        await Timer(1, "ns")
        assert cocotb.utils.get_sim_time(units="ns") == start_time + 1

    coro = cocotb.scheduler.start_soon(coro())

    await coro


@cocotb.test()
async def test_kill_start_soon_task(_):
    """Test killing task queued by start_soon."""
    coro_scheduled = False

    async def coro():
        nonlocal coro_scheduled
        coro_scheduled = True

    task = cocotb.scheduler.start_soon(coro())
    task.kill()

    await NullTrigger()
    assert coro_scheduled is False
    assert task._finished


start_soon_started = False


@cocotb.test()
async def test_test_end_after_start_soon(_):
    """Test ending test before start_soon queued coroutine starts."""
    async def coro():
        global start_soon_started
        start_soon_started = True

    cocotb.scheduler.start_soon(coro())


@cocotb.test()
async def test_previous_start_soon_not_scheduled(_):
    """Test that queued coroutine from previous test did not run.

    NOTE: This test must be after test_test_end_after_start_soon.
    """
    assert start_soon_started is False
