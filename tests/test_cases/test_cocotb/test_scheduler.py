# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Test for scheduler and coroutine behavior

* fork
* join
* kill
"""

import contextlib
import logging
import os
import re
from asyncio import CancelledError, InvalidStateError
from typing import Any, Awaitable, Coroutine

import pytest
from common import MyException, assert_takes

import cocotb
from cocotb.clock import Clock
from cocotb.task import Task
from cocotb.triggers import (
    Combine,
    Event,
    First,
    NullTrigger,
    RisingEdge,
    Timer,
    Trigger,
)

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test()
async def test_task_kill(dut):
    """Test that killing a task causes pending task to continue"""

    test_flag = False

    async def waiter(task):
        try:
            await task
        finally:
            nonlocal test_flag
            test_flag = True

    async def coro():
        await Timer(1000, "ns")

    task = cocotb.start_soon(coro())
    await Timer(1)
    waiter_task = cocotb.start_soon(waiter(task))
    await Timer(1)
    task.cancel()

    # task should be cancelled, but waiter_task hasn't resumed yet
    await NullTrigger()
    assert task.cancelled()
    assert not waiter_task.done()
    assert not test_flag

    # waiter should resume and finish
    await NullTrigger()
    assert waiter_task.done()
    assert test_flag


# worst case wait is max(time of task_one, time of task_two)
# worst case of task_one is 5*(clock+wait) = 5*(10+100) = 550
# worst case of task_two is 5*(clock+wait) = 5*(10+1000) = 5050
@cocotb.test(timeout_time=5100, timeout_unit="ns")
async def test_task_close_down(dut) -> None:
    """Test tasks completing allows awaiting task to continue."""

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    async def wait_on_clock_and_timer(time_ns: int) -> None:
        for _ in range(5):
            await RisingEdge(dut.clk)
            await Timer(time_ns, "ns")

    task_one = cocotb.start_soon(wait_on_clock_and_timer(time_ns=100))
    task_two = cocotb.start_soon(wait_on_clock_and_timer(time_ns=1000))

    await task_one
    await task_two


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

    task = cocotb.start_soon(some_coro())

    retval = 1
    x = await task
    assert x == 1

    # joining the second time should give the same result.
    # we change retval here to prove it does not run again
    retval = 2
    x = await task
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
        return cycles

    cocotb.start_soon(Clock(dut.clk, 2000, "ps").start())

    short_wait = cocotb.start_soon(wait_for(dut.clk, 10))
    long_wait = cocotb.start_soon(wait_for(dut.clk, 30))

    a = await wait_for(dut.clk, 20)
    assert a == 20
    b = await short_wait
    assert b == 10
    c = await long_wait
    assert c == 30


@cocotb.test()
async def test_kill_twice(dut):
    """
    Test that killing a coroutine that has already been killed does not crash
    """

    async def coro() -> None:
        await Timer(100, "ns")

    task = cocotb.start_soon(coro())
    await Timer(1, "ns")
    task.cancel()
    await Timer(1, "ns")
    task.cancel()


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
    dut.clk.value = 0

    victim_resumed = False

    async def victim():
        await Timer(1, "step")  # prevent scheduling of RisingEdge before killer
        await RisingEdge(dut.clk)
        nonlocal victim_resumed
        victim_resumed = True

    victim_task = cocotb.start_soon(victim())

    async def killer():
        await RisingEdge(dut.clk)
        victim_task.cancel()

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
            log.info("Fork %d, iteration %d, last fork was %s", n, i, last_fork)
            assert last_fork != n
            last_fork = n
            await NullTrigger()

    # Test should start in event loop
    await Combine(*(cocotb.start_soon(reschedule(i)) for i in range(4)))

    await Timer(1, "ns")

    # Event loop when simulator returns
    await Combine(*(cocotb.start_soon(reschedule(i)) for i in range(4)))


@cocotb.test()
async def test_nulltrigger_repr(_):
    n = NullTrigger()
    assert re.match(r"<NullTrigger at \w+>", repr(n))
    n = NullTrigger(name="my_nulltrigger")
    assert re.match(r"<NullTrigger for my_nulltrigger at \w+>", repr(n))


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

    cocotb.start_soon(waiter(e))
    await NullTrigger()

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
    await Timer(1, "ns")
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

    await Timer(1, "ns")

    assert dut.array_7_downto_4.value == [10, 2, 3, 4]


@cocotb.test
async def test_task_repr(_) -> None:
    """Test Task.__repr__."""
    log = logging.getLogger("cocotb.test")

    coro_e = Event()

    async def coroutine_wait():
        await Timer(1, unit="ns")

    async def coroutine_inner():
        await coro_e.wait()
        # cr_await is None while the coroutine is running, so we can't get the stack...
        log.info(repr(coro_task))
        assert re.match(r"<Task \d+ running coro=coroutine_outer\(\)>", repr(coro_task))

        await Combine(*(cocotb.start_soon(coroutine_wait()) for _ in range(2)))

        return "Combine done"

    async def coroutine_middle():
        return await coroutine_inner()

    async def coroutine_outer():
        return await coroutine_middle()

    coro_task = cocotb.start_soon(coroutine_outer())
    await NullTrigger()

    # let coroutine_inner run up to the await Combine
    coro_e.set()
    await NullTrigger()

    log.info(repr(coro_task))
    assert re.match(
        (
            r"<Task \d+ pending coro=coroutine_inner\(\) trigger=Combine\("
            r"<Task \d+ scheduled coro=coroutine_wait\(\)>, "
            r"<Task \d+ scheduled coro=coroutine_wait\(\)>"
            r"\)>"
        ),
        repr(coro_task),
    )

    # wait for coroutine_waits to start
    await NullTrigger()

    log.info(repr(coro_task))
    assert re.match(
        (
            r"<Task \d+ pending coro=coroutine_inner\(\) trigger=Combine\("
            r"<Task \d+ pending coro=coroutine_wait\(\) trigger=<Timer of 1000.00ps at \w+>>, "
            r"<Task \d+ pending coro=coroutine_wait\(\) trigger=<Timer of 1000.00ps at \w+>>"
            r"\)>"
        ),
        repr(coro_task),
    )

    await Timer(2, unit="ns")

    log.info(repr(coro_task))
    assert re.match(
        r"<Task \d+ finished coro=coroutine_outer\(\) outcome=Value\('Combine done'\)",
        repr(coro_task),
    )

    async def coroutine_first():
        task = Task(coroutine_wait())
        await First(task, Timer(2, unit="ns"))
        task.cancel()

    coro_task = cocotb.start_soon(coroutine_first())
    assert re.match(r"<Task \d+ scheduled coro=coroutine_first\(\)>", repr(coro_task))

    await NullTrigger()

    log.info(repr(coro_task))
    assert re.match(
        (
            r"<Task \d+ pending coro=coroutine_first\(\) trigger=First\("
            r"<Task \d+ created coro=coroutine_wait\(\)>, "
            r"<Timer of 2000.00ps at \w+>"
            r"\)>"
        ),
        repr(coro_task),
    )

    # wait for coroutine_wait to start
    await NullTrigger()  # start_soon on _wait_callback

    log.info(repr(coro_task))
    assert re.match(
        (
            r"<Task \d+ pending coro=coroutine_first\(\) trigger=First\("
            r"<Task \d+ scheduled coro=coroutine_wait\(\)>, "
            r"<Timer of 2000.00ps at \w+>"
            r"\)>"
        ),
        repr(coro_task),
    )

    await NullTrigger()  # awaiting Task in _wait_callback

    log.info(repr(coro_task))
    assert re.match(
        (
            r"<Task \d+ pending coro=coroutine_first\(\) trigger=First\("
            r"<Task \d+ pending coro=coroutine_wait\(\) trigger=<Timer of 1000.00ps at \w+>>, "
            r"<Timer of 2000.00ps at \w+>"
            r"\)>"
        ),
        repr(coro_task),
    )

    async def coroutine_timer():
        await Timer(1, unit="ns")

    coro_task = cocotb.start_soon(coroutine_timer())
    await NullTrigger()

    # Trigger.__await__ should be popped from the coroutine stack
    log.info(repr(coro_task))
    assert re.match(
        r"<Task \d+ pending coro=coroutine_timer\(\) trigger=<Timer of 1000.00ps at \w+>>",
        repr(coro_task),
    )

    # start task
    coro_task = cocotb.start_soon(coroutine_outer())

    log.info(repr(coro_task))
    assert re.match(r"<Task \d+ scheduled coro=coroutine_outer\(\)>", repr(coro_task))

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

    object_task.cancel()  # prevent RuntimeWarning of unwatched coroutine
    await NullTrigger()


@cocotb.test()
async def test_test_repr(_):
    """Test RunningTest.__repr__"""
    log = logging.getLogger("cocotb.test")

    current_test = cocotb._regression_manager._running_test._main_task
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

        current_test = cocotb._regression_manager._running_test._main_task
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
        cocotb._scheduler_inst._sim_react(trigger)
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
        await Timer(1, "ns")

    coro = cocotb.start_soon(coro())

    with assert_takes(1, "ns"):
        await coro


@cocotb.test()
async def test_kill_start_soon_task(_):
    """Test killing task queued by start_soon."""
    coro_scheduled = False

    async def coro():
        nonlocal coro_scheduled
        coro_scheduled = True

    task = cocotb.start_soon(coro())
    task.cancel()

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


@cocotb.test
async def test_start(_) -> None:
    async def coro():
        await Timer(1, "step")

    task1 = cocotb.start_soon(coro())
    assert type(task1) is Task
    assert not task1.done()

    await Timer(2, "step")
    assert task1.done()

    task2 = cocotb.create_task(coro())
    task3 = cocotb.start_soon(task2)
    assert task3 is task2

    async def coro_val():
        return 1

    task6 = cocotb.start_soon(coro_val())
    await NullTrigger()
    assert task6.done()
    assert await task6 == 1


@cocotb.test
async def test_start_scheduling(_) -> None:
    """Test that start resumes calling task before control is yielded to simulator."""
    sim_resumed = False
    coro_started = False

    def react_wrapper(trigger):
        """Function to prime trigger with."""
        nonlocal sim_resumed
        log = logging.getLogger("cocotb.test")
        log.debug("react_wrapper start")
        sim_resumed = False
        cocotb._scheduler_inst._sim_react(trigger)
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
    cocotb.start_soon(coro())
    assert coro_started is False
    await NullTrigger()
    assert sim_resumed is False
    assert coro_started is True
    await Timer(1, "step")  # await a GPITrigger to ensure control returns to simulator
    assert sim_resumed is True


@cocotb.test()
async def test_create_task(_):
    # proper construction from coroutines
    async def coro():
        pass

    assert type(cocotb.create_task(coro())) is Task

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

    assert type(cocotb.create_task(CoroType())) is Task

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
async def test_cancel_task(_: object) -> None:
    cancelled: bool = False

    async def coro(will_be_cancelled: bool) -> None:
        try:
            await Timer(10, "ns")
        except CancelledError:
            nonlocal cancelled
            cancelled = True
            raise
        else:
            assert not will_be_cancelled

    # Test Task succeeds successfully.
    task = cocotb.start_soon(coro(False))
    assert not cancelled
    assert not task.cancelled()
    assert not task.done()
    await task
    assert not cancelled
    assert not task.cancelled()
    assert task.done()

    cancelled = False
    task = cocotb.start_soon(coro(True))
    await NullTrigger()
    task.cancel("msg1234")
    await Timer(1, "ns")
    assert cancelled
    assert task.cancelled()
    assert task.done()
    with pytest.raises(CancelledError, match="msg1234"):
        task.result()
    with pytest.raises(CancelledError, match="msg1234"):
        task.exception()

    # Test cancel before task starts
    task = cocotb.start_soon(coro(True))
    task.cancel()
    await Timer(1, "ns")
    assert cancelled
    assert task.cancelled()
    assert task.done()


@cocotb.test(expect_error=RuntimeError)
async def test_cancel_task_cancellation_error(_: object) -> None:
    a = Event()

    async def coro():
        with contextlib.suppress(CancelledError):
            await a.wait()

    task = cocotb.start_soon(coro())
    await NullTrigger()
    task.cancel()
    await Timer(1, "ns")


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
async def test_task_done_callback_passing(_) -> None:
    callback_ran = False

    def done_callback(_: Task) -> None:
        nonlocal callback_ran
        callback_ran = True

    async def passing_coro() -> None:
        pass

    passing_task = cocotb.start_soon(passing_coro())
    passing_task._add_done_callback(done_callback)
    await passing_task
    assert callback_ran


@cocotb.test
async def test_task_done_callback_erroring(_) -> None:
    callback_ran = False

    def done_callback(_: Task) -> None:
        nonlocal callback_ran
        callback_ran = True

    async def erroring_coro() -> None:
        raise Exception

    erroring_task = cocotb.start_soon(erroring_coro())
    callback_ran = False
    erroring_task._add_done_callback(done_callback)
    with contextlib.suppress(Exception):
        await erroring_task
    assert callback_ran


@cocotb.test
async def test_task_done_callback_cancelled(_) -> None:
    callback_ran = False

    def done_callback(_: Task) -> None:
        nonlocal callback_ran
        callback_ran = True

    async def cancelled_coro() -> None:
        e = Event()
        await e.wait()

    cancelled_task = cocotb.start_soon(cancelled_coro())
    callback_ran = False
    cancelled_task._add_done_callback(done_callback)
    await Timer(1, "ns")
    cancelled_task.cancel()
    await NullTrigger()
    assert callback_ran


@cocotb.test
async def test_task_done_callback_added_after_done(_) -> None:
    async def noop() -> None:
        pass

    callback_ran = False

    def done_callback(_: Task) -> None:
        nonlocal callback_ran
        callback_ran = True

    task = cocotb.start_soon(noop())
    await task
    task._add_done_callback(done_callback)
    await NullTrigger()
    assert callback_ran


@cocotb.test
async def test_task_complete(_) -> None:
    async def noop() -> None:
        pass

    task = cocotb.start_soon(noop())
    assert not task.done()
    tc = task.complete
    assert tc.task is task
    res = await tc
    assert res is tc
    assert res is task.complete
    assert task.done()


@cocotb.test
async def test_joins_in_first(_) -> None:
    async def wait(ns: int) -> None:
        await Timer(ns, "ns")

    task1 = cocotb.start_soon(wait(10))
    task2 = cocotb.start_soon(wait(20))
    j = await First(task1.complete, task2.complete)
    assert j is task1.complete


@cocotb.test(expect_error=MyException)
async def test_start_after_create(_) -> None:
    async def fail():
        raise MyException()

    a = cocotb.create_task(fail())
    cocotb.start_soon(a)
    await a


@cocotb.test
async def test_start_again_while_scheduled(_) -> None:
    async def noop() -> None:
        pass

    a = cocotb.start_soon(noop())
    b = cocotb.start_soon(a)
    assert b is a
    await a


@cocotb.test
async def test_start_again_while_pending(_) -> None:
    async def noop() -> None:
        await Timer(1, "ns")

    a = cocotb.start_soon(noop())
    await NullTrigger()
    b = cocotb.start_soon(a)
    assert b is a
    await a


@cocotb.test(expect_error=RuntimeError)
async def test_test_end_cancellation_error(_) -> None:
    """Test that test-end Cancellation causes test failure."""

    async def coro() -> None:
        with contextlib.suppress(CancelledError):
            await Timer(1000, "ns")

    cocotb.start_soon(coro())
    await Timer(1)
