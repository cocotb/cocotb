.. _coroutines:
.. _async_functions:

.. spelling:word-list::
   Async


********************
Coroutines and Tasks
********************

Testbenches built using cocotb use Python coroutines.
*Tasks* are cocotb objects that wrap coroutines
and are used to schedule concurrent execution of the testbench coroutines.

While active tasks are executing, the simulation is paused.
The coroutine uses the :keyword:`await` keyword to
block on another coroutine's execution or pass control of execution back to the
simulator, allowing simulation time to advance.

Typically coroutines :keyword:`await` a :class:`~cocotb.triggers.Trigger` object which
pauses the task, and indicates to the simulator some event which will cause the task to resume execution.
For example:

.. code-block:: python3

    async def wait_10ns():
        cocotb.log.info("About to wait for 10 ns")
        await Timer(10, units='ns')
        cocotb.log.info("Simulation time has advanced by 10 ns")

Coroutines may also :keyword:`await` on other coroutines:

.. code-block:: python3

    async def wait_100ns():
        for i in range(10):
            await wait_10ns()

Coroutines can :keyword:`return` a value, so that they can be used by other coroutines.

.. code-block:: python3

    async def get_signal(clk, signal):
        await RisingEdge(clk)
        return signal.value

    async def check_signal_changes(dut):
        first = await get_signal(dut.clk, dut.signal)
        second = await get_signal(dut.clk, dut.signal)
        assert first != second, "Signal did not change"

Concurrent Execution
====================

Coroutines can be scheduled for concurrent execution with :func:`~cocotb.fork`, :func:`~cocotb.start`, and :func:`~cocotb.start_soon`.

:func:`~cocotb.fork` (deprecated) schedules and executes the new coroutine immediately,
returning control to the calling task after the new coroutine finishes or yields control.
No other pending tasks are run.

The *async* function :func:`~cocotb.start` schedules the new coroutine to be executed concurrently,
then yields control to allow the new task (and any other pending tasks) to run,
before resuming the calling task.

:func:`~cocotb.start_soon` schedules the new coroutine for future execution,
after the calling task yields control.

.. note::
    The preferred way to schedule tasks is with :func:`~cocotb.start` and :func:`~cocotb.start_soon`.
    :func:`~cocotb.fork` is deprecated and will be removed in a future version of cocotb.

.. code-block:: python3

    @cocotb.test()
    async def test_act_during_reset(dut):
        """While reset is active, toggle signals"""
        tb = uart_tb(dut)
        # "Clock" is a built in class for toggling a clock signal
        cocotb.start_soon(Clock(dut.clk, 1, units='ns').start())
        # reset_dut is a function -
        # part of the user-generated "uart_tb" class
        # run reset_dut immediately before continuing
        await cocotb.start(tb.reset_dut(dut.rstn, 20))

        await Timer(10, units='ns')
        print("Reset is still active: %d" % dut.rstn)
        await Timer(15, units='ns')
        print("Reset has gone inactive: %d" % dut.rstn)

Other tasks can be used in an :keyword:`await` statement to suspend the current task until the other task finishes.

.. code-block:: python3

    @cocotb.test()
    async def test_count_edge_cycles(dut, period_ns=1, clocks=6):
        cocotb.start_soon(Clock(dut.clk, period_ns, units='ns').start())
        await RisingEdge(dut.clk)

        timer = Timer(period_ns + 10, 'ns')
        task = cocotb.start_soon(count_edges_cycles(dut.clk, clocks))
        count = 0
        expect = clocks - 1

        while True:
            result = await First(timer, task)
            if count > expect:
                raise TestFailure("Task didn't complete in expected time")
            if result is timer:
                dut._log.info("Count %d: Task still running" % count)
                count += 1
            else:
                break

Tasks can be killed before they complete,
forcing their completion before they would naturally end.

.. code-block:: python3

    @cocotb.test()
    async def test_different_clocks(dut):
        clk_1mhz   = Clock(dut.clk, 1.0, units='us')
        clk_250mhz = Clock(dut.clk, 4.0, units='ns')

        clk_gen = cocotb.start_soon(clk_1mhz.start())
        start_time_ns = get_sim_time(units='ns')
        await Timer(1, units='ns')
        await RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(units='ns')
        if not isclose(edge_time_ns, start_time_ns + 1000.0):
            raise TestFailure("Expected a period of 1 us")

        clk_gen.kill()  # kill clock coroutine here

        clk_gen = cocotb.start_soon(clk_250mhz.start())
        start_time_ns = get_sim_time(units='ns')
        await Timer(1, units='ns')
        await RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(units='ns')
        if not isclose(edge_time_ns, start_time_ns + 4.0):
            raise TestFailure("Expected a period of 4 ns")


.. versionchanged:: 1.4
    The :any:`cocotb.coroutine` decorator is no longer necessary for ``async def`` coroutines.
    ``async def`` coroutines can be used, without the ``@cocotb.coroutine`` decorator, wherever decorated coroutines are accepted,
    including :keyword:`yield` statements and :func:`cocotb.fork`.

.. versionchanged:: 1.6
    Added :func:`cocotb.start` and :func:`cocotb.start_soon` scheduling functions.

.. versionchanged:: 1.7
    Deprecated :func:`cocotb.fork`.


Async generators
================

In Python 3.6, a ``yield`` statement within an ``async`` function has a new
meaning (rather than being a ``SyntaxError``) which matches the typical meaning
of ``yield`` within regular Python code. It can be used to create a special
type of generator function that can be iterated with ``async for``:

.. code-block:: python3

    async def ten_samples_of(clk, signal):
        for i in range(10):
            await RisingEdge(clk)
            yield signal.value  # this means "send back to the for loop"

    @cocotb.test()
    async def test_samples_are_even(dut):
        async for sample in ten_samples_of(dut.clk, dut.signal):
            assert sample % 2 == 0

More details on this type of generator can be found in :pep:`525`.


.. _yield-syntax:

Generator-based coroutines
==========================

.. note:: This style is no longer recommended and support may someday be removed.

Prior to Python 3.5, and the introduction of :keyword:`async` and :keyword:`await`, coroutines were implemented as wrappers around generators.
Coroutine functions would be decorated with :class:`~cocotb.coroutine` and would use :keyword:`yield` to block on other coroutines or triggers.
You may see existing code that uses this syntax for coroutines, but do not worry, it is compatible with :keyword:`async` coroutines.

Any object that can be used in an :keyword:`await` statement can also be used in a :keyword:`yield` statement while in a generator-based coroutine;
including triggers like :class:`~cocotb.triggers.Timer`.

.. code-block:: python3

    @cocotb.coroutine
    def simple_clock(signal, half_period, half_period_units):
        signal.value = 0
        timer = Timer(half_period, half_period_units)
        while True:
            # in generator-based coroutines triggers are yielded
            yield timer
            signal.value = ~signal

Likewise, any place that will accept :keyword:`async` coroutines will also accept generator-based coroutines;
including :func:`~cocotb.fork`.

.. code-block:: python3

    @cocotb.coroutine
    def start_clock(clk):
        # generator-based coroutines can still be forked
        cocotb.start_soon(simple_clock(clk, 5, units='ns'))
        yield RisingEdge(clk)

:keyword:`async` coroutines can be yielded in generator-based coroutines.

.. code-block:: python3

    async def detect_transaction(clk, valid):
        await RisingEdge(clk)
        while not valid.value:
            await RisingEdge(clk)

    @cocotb.coroutine
    def monitor(clk, valid, data):
        # async coroutines can be yielded
        yield detect_transaction(clk, valid)
        return data.value

Generator-based coroutines can also be awaited in :keyword:`async` coroutines.

.. code-block:: python3

    async def check_incrementing(clk, valid, data):
        # generator-based coroutines can be awaited
        prev_count = await monitor()
        while True:
            count = await monitor()
            assert count == (prev_count + 1)
            prev_count = count

You may also see syntax like ``yield [trigger_a, trigger_b, ...]``, which is syntactic sugar for :class:`~cocotb.triggers.First`.

.. code-block:: python3

    @cocotb.coroutine
    def run_for(coro, time, units):
        timeout = Timer(time, units='ps')
        # block until first trigger fires
        yield [timeout, coro]

Tests can also be generator-based coroutines.
Tests are not required to be decorated with :class:`~cocotb.coroutine` as the :class:`~cocotb.test` decorator will handle this case automatically.

.. code-block:: python3

    # just need the test decorator
    @cocotb.test()
    def run_test(dut):
        yield start_clock(dut.clk)
        checker = check_incrementing(
            clk=dut.clk,
            valid=dut.valid,
            data=dut.cnt)
        yield run_for(checker, 1, 'us')
