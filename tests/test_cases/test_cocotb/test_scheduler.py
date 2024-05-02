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
import os
import re
from asyncio import CancelledError, InvalidStateError
from typing import Any, Awaitable, Coroutine

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.task import CancellationError, Task
from cocotb.triggers import (
    Combine,
    Event,
    First,
    Join,
    NullTrigger,
    ReadOnly,
    RisingEdge,
    Timer,
    Trigger,
)
from common import MyException

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()

test_flag = False


async def clock_yield(generator):
    global test_flag
    await Join(generator)
    test_flag = True


@cocotb.test()
async def test_coroutine_kill(dut):
    """Test that killing a coroutine causes pending routine continue"""
    clk_gen = cocotb.start_soon(Clock(dut.clk, 100, "ns").start())
    await Timer(100, "ns")
    cocotb.start_soon(clock_yield(clk_gen))
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
    cocotb.start_soon(Clock(dut.clk, 100, "ns").start())

    coro_one = cocotb.start_soon(clock_one(dut))
    coro_two = cocotb.start_soon(clock_two(dut))

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

    coro = cocotb.start_soon(some_coro())

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

    cocotb.start_soon(Clock(dut.clk, 2000, "ps").start())

    short_wait = cocotb.start_soon(wait_for(dut.clk, 10))
    long_wait = cocotb.start_soon(wait_for(dut.clk, 30))

    await wait_for(dut.clk, 20)
    a = await short_wait.join()
    b = await long_wait.join()
    assert a == b == 3


@cocotb.test()
async def test_kill_twice(dut):
    """
    Test that killing a coroutine that has already been killed does not crash
    """
    clk_gen = cocotb.start_soon(Clock(dut.clk, 100, "ns").start())
    await Timer(1, "ns")
    clk_gen.kill()
    await Timer(1, "ns")
    clk_gen.kill()


@cocotb.test()
async def test_join_identity(dut):
    """
    Test that Join() returns the same object each time
    """
    clk_gen = cocotb.start_soon(Clock(dut.clk, 100, "ns").start())

    assert Join(clk_gen) is Join(clk_gen)
    await Timer(1, "ns")
    clk_gen.kill()


@cocotb.test()
async def test_trigger_with_failing_prime(dut):
    """Test that a trigger failing to prime throws"""

    class ABadTrigger(Trigger):
        def __init__(self):
            super().__init__()

        def _prime(self, callback):
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

    coros = [cocotb.start_soon(simple_coroutine()) for _ in range(1024)]

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

    victim_task = cocotb.start_soon(victim())

    async def killer():
        await RisingEdge(dut.clk)
        victim_task.kill()

    cocotb.start_soon(killer())

    await Timer(
        2, "step"
    )  # allow Timer in victim to pass making it schedule RisingEdge after the killer
    dut.clk.value = 1
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

    async def reschedule(n):
        nonlocal last_fork
        for i in range(4):
            log.info(f"Fork {n}, iteration {i}, last fork was {last_fork}")
            assert last_fork != n
            last_fork = n
            await NullTrigger()

    # Test should start in event loop
    await Combine(*(cocotb.start_soon(reschedule(i)) for i in range(4)))

    await Timer(1, "ns")

    # Event loop when simulator returns
    await Combine(*(cocotb.start_soon(reschedule(i)) for i in range(4)))


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

    await cocotb.start(waiter(e))

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
    dut.stream_in_data.value = 0
    await Timer(10, "ns")
    assert dut.stream_in_data.value == 0
    dut.stream_in_data.value = 1
    dut.stream_in_data.value = 2
    await ReadOnly()
    assert dut.stream_in_data.value == 2


# GHDL unable to put values on nested array types (gh-2588)
@cocotb.test(
    expect_error=Exception if cocotb.SIM_NAME.lower().startswith("ghdl") else ()
)
async def test_last_scheduled_write_wins_array(dut):
    """
    Test that the last scheduled write for an *arrayed* signal handle is the value that is written.
    """
    dut.array_7_downto_4.value = [1, 2, 3, 4]
    dut.array_7_downto_4[7].value = 10

    await ReadOnly()

    assert dut.array_7_downto_4.value == [10, 2, 3, 4]


# Most simulators do not support setting the value of a single bit of a packed array
@cocotb.test(
    skip=not cocotb.SIM_NAME.lower().startswith(("modelsim", "riviera"))
    or LANGUAGE != "vhdl"
)
async def test_last_scheduled_write_wins_array_handle_alias(dut):
    """
    Tests case where handles in the scheduled writes cache in the scheduler alias
    """
    dut.array_7_downto_4.value = [0, 0, 0, 0]
    dut.array_7_downto_4[7][0].value = 1

    await ReadOnly()

    assert dut.array_7_downto_4.value == [1, 0, 0, 0]


@cocotb.test()
async def test_task_repr(dut):
    """Test Task.__repr__."""
    log = logging.getLogger("cocotb.test")

    coro_e = Event("coroutine_inner")

    async def coroutine_wait():
        await Timer(1, units="ns")

    async def coroutine_inner():
        await coro_e.wait()
        this_task = coro_e.data
        # cr_await is None while the coroutine is running, so we can't get the stack...
        log.info(repr(this_task))
        assert re.match(r"<Task \d+ running coro=coroutine_outer\(\)>", repr(this_task))

        await Combine(*(cocotb.start_soon(coroutine_wait()) for _ in range(2)))

        return "Combine done"

    async def coroutine_middle():
        return await coroutine_inner()

    async def coroutine_outer():
        return await coroutine_middle()

    coro_task = await cocotb.start(coroutine_outer())

    coro_e.set(coro_task)

    await NullTrigger()

    log.info(repr(coro_task))
    assert re.match(
        r"<Task \d+ pending coro=coroutine_inner\(\) trigger=Combine\(Join\(<Task \d+>\), Join\(<Task \d+>\)\)>",
        repr(coro_task),
    )

    await Timer(2, units="ns")

    log.info(repr(coro_task))
    assert re.match(
        r"<Task \d+ finished coro=coroutine_outer\(\) outcome=Value\('Combine done'\)",
        repr(coro_task),
    )

    async def coroutine_first():
        task = Task(coroutine_wait())
        await First(task, Timer(2, units="ns"))
        task.kill()

    coro_task = await cocotb.start(coroutine_first())

    log.info(repr(coro_task))
    assert re.match(
        r"<Task \d+ pending coro=coroutine_first\(\) trigger=First\(Join\(<Task \d+>\), <Timer of 2000.00ps at \w+>\)>",
        repr(coro_task),
    )

    async def coroutine_timer():
        await Timer(1, units="ns")

    coro_task = await cocotb.start(coroutine_timer())

    # Trigger.__await__ should be popped from the coroutine stack
    log.info(repr(coro_task))
    assert re.match(
        r"<Task \d+ pending coro=coroutine_timer\(\) trigger=<Timer of 1000.00ps at \w+>>",
        repr(coro_task),
    )

    # created but not scheduled yet
    coro_task = cocotb.start_soon(coroutine_outer())

    log.info(repr(coro_task))
    assert re.match(r"<Task \d+ created coro=coroutine_outer\(\)>", repr(coro_task))

    log.info(str(coro_task))
    assert re.match(r"<Task \d+>", str(coro_task))

    class CoroutineClass(Coroutine):
        def __init__(self):
            self._coro = self.run()

        async def run(self):
            pass

        def send(self, value):
            self._coro.send(value)

        def throw(self, exception):
            self._coro.throw(exception)

        def close(self):
            self._coro.close()

        def __await__(self):
            yield from self._coro.__await__()

    object_task = cocotb.create_task(CoroutineClass())
    log.info(repr(object_task))
    assert re.match(r"<Task \d+ created coro=CoroutineClass\(\)>", repr(object_task))

    object_task.kill()  # prevent RuntimeWarning of unwatched coroutine


@cocotb.test()
async def test_test_repr(_):
    """Test RunningTest.__repr__"""
    log = logging.getLogger("cocotb.test")

    current_test = cocotb._scheduler._test
    log.info(repr(current_test))
    assert re.match(
        r"<Test test_test_repr running coro=test_test_repr\(\)>", repr(current_test)
    )

    log.info(str(current_test))
    assert re.match(r"<Test test_test_repr>", str(current_test))


@cocotb.test()
class TestClassRepr(Coroutine):
    def __init__(self, dut):
        self._coro = self.check_repr(dut)

    async def check_repr(self, dut):
        log = logging.getLogger("cocotb.test")

        current_test = cocotb._scheduler._test
        log.info(repr(current_test))
        assert re.match(
            r"<Test TestClassRepr running coro=TestClassRepr\(\)>", repr(current_test)
        )

        log.info(str(current_test))
        assert re.match(r"<Test TestClassRepr>", str(current_test))

    def send(self, value):
        self._coro.send(value)

    def throw(self, exception):
        self._coro.throw(exception)

    def close(self):
        self._coro.close()

    def __await__(self):
        yield from self._coro.__await__()


@cocotb.test()
async def test_start_soon_async(_):
    """Tests start_soon works with coroutines"""
    a = 0

    async def example():
        nonlocal a
        a = 1

    cocotb.start_soon(example())
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
        cocotb._scheduler._react(trigger)
        assert coro_scheduled is True
        log.debug("react_wrapper end")

    async def coro():
        nonlocal coro_scheduled
        coro_scheduled = True

    t = Timer(1, "step")
    # pre-prime with wrapper function instead of letting scheduler prime it normally
    t._prime(react_wrapper)
    await t
    # react_wrapper is now on the stack
    cocotb.start_soon(coro())  # coro() should run before returning to the simulator
    await Timer(1, "step")  # await a GPITrigger to ensure control returns to simulator
    assert coro_scheduled is True


@cocotb.test()
async def test_await_start_soon(_):
    """Test awaiting start_soon queued coroutine before it starts."""

    async def coro():
        start_time = cocotb.utils.get_sim_time(units="ns")
        await Timer(1, "ns")
        assert cocotb.utils.get_sim_time(units="ns") == start_time + 1

    coro = cocotb.start_soon(coro())

    await coro


@cocotb.test()
async def test_kill_start_soon_task(_):
    """Test killing task queued by start_soon."""
    coro_scheduled = False

    async def coro():
        nonlocal coro_scheduled
        coro_scheduled = True

    task = cocotb.start_soon(coro())
    task.kill()

    await NullTrigger()
    assert coro_scheduled is False
    assert task.done()


start_soon_started = False


@cocotb.test()
async def test_test_end_after_start_soon(_):
    """Test ending test before start_soon queued coroutine starts."""

    async def coro():
        global start_soon_started
        start_soon_started = True

    cocotb.start_soon(coro())


@cocotb.test()
async def test_previous_start_soon_not_scheduled(_):
    """Test that queued coroutine from previous test did not run.

    NOTE: This test must be after test_test_end_after_start_soon.
    """
    assert start_soon_started is False


@cocotb.test()
async def test_test_end_with_multiple_pending_tasks(_):
    """Test ending a test with multiple tasks queued by start_soon."""

    async def coro():
        return 0

    # gh-3354
    cocotb.start_soon(coro())
    cocotb.start_soon(coro())


@cocotb.test()
async def test_start(_):
    async def coro():
        await Timer(1, "step")

    task1 = await cocotb.start(coro())
    assert type(task1) is Task
    assert task1.has_started()
    assert not task1.done()

    await Timer(1, "step")
    assert task1.done()

    task2 = cocotb.create_task(coro())
    task3 = await cocotb.start(task2)
    assert task3 is task2

    await Timer(1, "step")

    task4 = cocotb.start_soon(coro())
    assert not task4.has_started()
    await cocotb.start(coro())
    assert task4.has_started()
    await Timer(1, "step")
    assert task4.done()

    async def coro_val():
        return 1

    task6 = await cocotb.start(coro_val())
    assert task6.done()
    assert await task6 == 1


@cocotb.test()
async def test_start_scheduling(dut):
    """Test that start resumes calling task before control is yielded to simulator."""
    sim_resumed = False
    coro_started = False

    def react_wrapper(trigger):
        """Function to prime trigger with."""
        nonlocal sim_resumed
        log = logging.getLogger("cocotb.test")
        log.debug("react_wrapper start")
        sim_resumed = False
        cocotb._scheduler._react(trigger)
        sim_resumed = True
        log.debug("react_wrapper end")

    async def coro():
        nonlocal coro_started
        coro_started = True

    t = Timer(1, "step")
    # pre-prime with wrapper function instead of letting scheduler prime it normally
    t._prime(react_wrapper)
    await t
    # react_wrapper is now on the stack
    assert sim_resumed is False
    await cocotb.start(coro())
    assert sim_resumed is False
    assert coro_started is True
    await Timer(1, "step")  # await a GPITrigger to ensure control returns to simulator
    assert sim_resumed is True


@cocotb.test()
async def test_create_task(_):
    # proper construction from coroutines
    async def coro():
        pass

    assert type(cocotb.create_task(coro())) == Task

    # proper construction from Coroutine objects
    class CoroType(Coroutine):
        def __init__(self):
            self._coro = coro()

        def send(self, value):
            return self._coro.send(value)

        def throw(self, exception):
            self._coro.throw(exception)

        def close(self):
            self._coro.close()

        def __await__(self):
            yield from self._coro.__await__()

    assert type(cocotb.create_task(CoroType())) == Task

    # fail if given async generators
    async def agen():
        yield None

    with pytest.raises(TypeError):
        cocotb.create_task(agen())

    # fail if given coroutine function
    with pytest.raises(TypeError):
        cocotb.create_task(coro)

    # fail if given Coroutine Type
    with pytest.raises(TypeError):
        cocotb.create_task(CoroType)

    # fail if given async generator function
    with pytest.raises(TypeError):
        cocotb.create_task(agen)

    # fail if given random type
    with pytest.raises(TypeError):
        cocotb.create_task(object())


@cocotb.test()
async def test_task_completes(_):
    async def coro():
        return 123

    task = cocotb.start_soon(coro())
    assert not task.cancelled()
    assert not task.done()
    assert await task == 123
    assert not task.cancelled()
    assert task.done()
    assert task.result() == 123
    assert task.exception() is None


@cocotb.test()
async def test_task_exception(_):
    async def coro():
        raise MyException("msg1234")

    task = cocotb.start_soon(coro())
    assert not task.cancelled()
    assert not task.done()
    with pytest.raises(MyException, match="msg1234"):
        await task
    assert not task.cancelled()
    assert task.done()
    with pytest.raises(MyException, match="msg1234"):
        task.result()
    assert type(task.exception()) is MyException
    assert str(task.exception()) == "msg1234"


@cocotb.test
async def test_cancel_task_methods(_):
    async def coro():
        return 0

    task = cocotb.start_soon(coro())
    assert not task.cancelled()
    assert not task.done()
    await task
    assert not task.cancelled()
    assert task.done()


@cocotb.test
async def test_cancel_task_running(_):
    async def coro2():
        try:
            await Timer(10, "ns")
        except CancelledError:
            raise
        assert False

    task = cocotb.start_soon(coro2())

    # wait until it's blocking to cancel
    await Timer(5, "ns")
    task.cancel("msg1234")
    await NullTrigger()

    # check output
    assert task.cancelled()
    with pytest.raises(CancelledError, match="msg1234"):
        task.result()
    with pytest.raises(CancelledError, match="msg1234"):
        task.exception()

    await Timer(10, "ns")
    # we'd get an error by now if the trigger weren't cleaned up


@cocotb.test
async def test_cancel_task_cancelled(_):
    async def coro():
        await Timer(10, "ns")
        assert False

    task = cocotb.start_soon(coro())

    # cancel it during await
    await Timer(5, "ns")
    task.cancel()
    await NullTrigger()

    assert task.done()
    assert task.cancelled()

    # try cancelling again to see if that hits the assert
    task.cancel()
    await NullTrigger()


@cocotb.test
async def test_cancel_task_scheduled(_):
    async def coro():
        assert False

    task = cocotb.start_soon(coro())

    # cancel before it runs
    with pytest.warns(RuntimeWarning):
        task.cancel()
    await NullTrigger()

    # will assert by now if not cancelled


@cocotb.test(expect_error=CancellationError)
async def test_cancel_task_suppress(_):
    async def coro():
        try:
            await Timer(10, "ns")
        except CancelledError:
            pass
        # will yield this because we squashed
        await Timer(1, "ns")

    task = cocotb.start_soon(coro())

    # cancel during first await
    await Timer(5, "ns")
    task.cancel()
    await NullTrigger()


@cocotb.test()
async def test_invalid_operations_task(_):
    async def coro():
        return 123

    task = cocotb.start_soon(coro())
    with pytest.raises(InvalidStateError):
        task.result()
    with pytest.raises(InvalidStateError):
        task.exception()


@cocotb.test(expect_fail=True)
async def test_multiple_concurrent_test_fails(_) -> None:
    async def call_error(thing: Awaitable[Any]) -> None:
        await thing
        assert False

    thing = Timer(1, "ns")
    cocotb.start_soon(call_error(thing))
    cocotb.start_soon(call_error(thing))
    await Timer(10, "ns")


@cocotb.test
async def test_shutdown_cancellation(dut):
    async def lol():
        e = Event()
        try:
            await e.wait()
        except CancelledError:
            raise MyException()

    cocotb.start_soon(lol())
    await NullTrigger()
