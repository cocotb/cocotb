.. _coroutines:
.. _async_functions:

.. spelling:word-list::
   Async


******************************
Coroutines, Tasks and Triggers
******************************

cocotb testbenches use Python's coroutines.
:dfn:`Tasks` are cocotb objects that wrap coroutines
and are used to schedule concurrent execution of the coroutines.

While active tasks are executing, the simulation is paused.
The coroutine uses the :keyword:`await` keyword to
block on another coroutine's execution or pass control of execution back to the
simulator, allowing simulation time to advance.

Typically coroutines :keyword:`!await` a :class:`~cocotb.triggers.Trigger` object which
pauses the task, and indicates to the simulator some event which will cause the task to resume execution.
In the following example, :class:`~cocotb.triggers.Timer` is such a trigger:

.. code-block:: python

    async def wait_10ns():
        cocotb.log.info("About to wait for 10 ns")
        await Timer(10, unit="ns")
        cocotb.log.info("Simulation time has advanced by 10 ns")

Coroutines may also :keyword:`!await` on other coroutines:

.. code-block:: python

    async def wait_100ns():
        for i in range(10):
            await wait_10ns()

Coroutines can :keyword:`return` a value, so that they can be used by other coroutines.

.. code-block:: python

    async def get_signal(clk, signal):
        await RisingEdge(clk)
        return signal.value

    async def check_signal_changes(dut):
        first = await get_signal(dut.clk, dut.signal)
        second = await get_signal(dut.clk, dut.signal)
        assert first != second, "Signal did not change"


Triggers and Concurrency Utilities
==================================

Below is a table of triggers and concurrency utilities that are useful for writing testbenches and models.

..
   Please keep this table aligned with the content in library_reference.rst

+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| **Signal Edges**                                                                                                                                 |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| | :class:`~cocotb.triggers.RisingEdge`               | | Resume after a *rising* edge on a single-bit signal                                     |
| | :class:`~cocotb.triggers.FallingEdge`              | | Resume after a *falling* edge on a single-bit signal                                    |
| | :class:`~cocotb.triggers.ValueChange`              | | Resume after *any* edge on a signal, but prefer using ``signal.value_change``           |
| | :class:`~cocotb.triggers.ClockCycles`              | | Resume after the specified number of transitions of a signal                            |
| | :class:`~cocotb.triggers.Edge`                     | | (deprecated, use ``signal.value_change`` instead)                                       |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| **Timing**                                                                                                                                       |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| | :class:`~cocotb.triggers.Timer`                    | | Resume after the specified time                                                         |
| | :class:`~cocotb.triggers.ReadOnly`                 | | Resume when the simulation timestep moves to the *read-only* phase                      |
| | :class:`~cocotb.triggers.ReadWrite`                | | Resume when the simulation timestep moves to the *read-write* phase                     |
| | :class:`~cocotb.triggers.NextTimeStep`             | | Resume when the simulation timestep moves to the *next time step*                       |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| **Concurrency**                                                                                                                                  |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| | :func:`~cocotb.triggers.gather`                    | | Resume after *all* given Tasks or Triggers                                              |
| | :func:`~cocotb.triggers.select`                    | | Resume after *any* given Tasks or Triggers                                              |
| | :class:`~cocotb.triggers.Combine`                  | | Resume after *all* given Triggers                                                       |
| | :class:`~cocotb.triggers.First`                    | | Resume after *any* given Triggers                                                       |
| | :meth:`Task.complete <cocotb.task.Task.complete>`  | | Resume when a Task completes                                                            |
| | :func:`~cocotb.triggers.wait` [#f1]_               | | Await on all given Tasks or Triggers concurrently and block until a condition is met    |
| | :class:`~cocotb.triggers.NullTrigger` [#f1]_       | | Resume "soon"                                                                           |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| **Synchronization**                                                                                                                              |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| | :class:`~cocotb.triggers.Event`                    | | A way to signal an event across Tasks                                                   |
| | :class:`~cocotb.triggers.Lock`                     | | A mutual exclusion lock                                                                 |
| | :func:`~cocotb.triggers.with_timeout`              | | Resume latest at the specified timeout time                                             |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+

.. rubric:: Footnotes

.. [#f1] Something for uncommon cases.

Concurrent Execution
====================

Coroutines can be scheduled for concurrent execution with :func:`~cocotb.start_soon`.
These concurrently running coroutines are called :class:`~cocotb.task.Task`\ s.

:func:`~cocotb.start_soon` schedules the coroutine for *future* execution,
some time after the current Task yields control.

.. code-block:: python

    @cocotb.test()
    async def test_act_during_reset(dut):
        """While reset is active, toggle signals"""
        tb = uart_tb(dut)
        # "Clock" is a built in class for toggling a clock signal
        Clock(dut.clk, 1, unit="ns").start()
        # reset_dut is a function -
        # part of the user-generated "uart_tb" class
        # run reset_dut immediately before continuing
        await tb.reset_dut(dut.rstn, 20)

        await Timer(10, unit="ns")
        print("Reset is still active: %d" % dut.rstn)
        await Timer(15, unit="ns")
        print("Reset has gone inactive: %d" % dut.rstn)

Other tasks can be used in an await statement to suspend the current task until the other task finishes.

.. code-block:: python

    @cocotb.test()
    async def test_count_edge_cycles(dut, period_ns=1, clocks=6):
        Clock(dut.clk, period_ns, unit="ns").start()
        await RisingEdge(dut.clk)

        timer = Timer(period_ns + 10, "ns")
        task = cocotb.start_soon(count_edges_cycles(dut.clk, clocks))
        count = 0
        expect = clocks - 1

        while True:
            result = await First(timer, task)
            assert count <= expect, "Task didn't complete in expected time"
            if result is timer:
                cocotb.log.info("Count %d: Task still running", count)
                count += 1
            else:
                break

Tasks can be killed before they complete,
forcing their completion before they would naturally end.

.. code-block:: python

    @cocotb.test()
    async def test_different_clocks(dut):
        clk_1mhz   = Clock(dut.clk, 1.0, unit="us")
        clk_250mhz = Clock(dut.clk, 4.0, unit="ns")

        clk_1mhz.start()
        start_time_ns = get_sim_time(unit="ns")
        await Timer(1, unit="ns")
        await RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(unit="ns")
        assert isclose(edge_time_ns, start_time_ns + 1000.0), "Expected a period of 1 us"

        clk_1mhz.stop()  # stop 1MHz clock here

        clk_250mhz.start()
        start_time_ns = get_sim_time(unit="ns")
        await Timer(1, unit="ns")
        await RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(unit="ns")
        assert isclose(edge_time_ns, start_time_ns + 4.0), "Expected a period of 4 ns"


.. versionchanged:: 1.4
    The ``cocotb.coroutine`` decorator is no longer necessary for :keyword:`async def` coroutines.
    :keyword:`async def` coroutines can be used, without the ``@cocotb.coroutine`` decorator, wherever decorated coroutines are accepted,
    including :keyword:`yield` statements and ``cocotb.fork`` (since replaced with :func:`~cocotb.start_soon`).

.. versionchanged:: 1.6
    Added :func:`cocotb.start` and :func:`cocotb.start_soon` scheduling functions.

.. versionchanged:: 1.7
    Deprecated ``cocotb.fork``.

.. versionchanged:: 2.0
    Removed ``cocotb.fork``.

.. versionchanged:: 2.0
    Removed ``cocotb.coroutine``.

.. versionremoved:: 2.0
    Removed references to the deprecated :func:`cocotb.start`.


Waiting For Multiple Events Simultaneously
==========================================

Occasionally you'll need to wait for either one of many Tasks or Triggers to fire,
or a collection of Tasks or Triggers to fire.
This is what :class:`~cocotb.triggers.First` and :class:`~cocotb.triggers.Combine` provide, respectively.


.. _first-tutorial:

Waiting For One Of Multiple Events
----------------------------------

:class:`~cocotb.triggers.First` is like awaiting multiple Triggers or Tasks at the same time,
and resumes after one of the Triggers or Tasks fires.
It returns the result of awaiting the Task or Trigger that fired first.
Below we see it used to implement a timeout.

.. code-block:: python

    @cocotb.test
    async def test_quiesce_or_timeout(dut):

        # generate stimulus and drive it to the design
        for trans in generate_transactions():
            await drive(dut.intf, trans)

        # wait for the design to quiesce or timeout
        timeout = Timer(10, "us")
        quiesce_task = cocotb.start_soon(quiesce())
        result = await First(timeout, quiesce_task)
        assert result is not timeout, "Design has hung!"

Fortunately for users timeouts are a common operation and cocotb provides :func:`~cocotb.triggers.with_timeout`.
The second section in the above code using it would be ``await with_timeout(quiesce(), 10, "us")``.

.. note::

    :class:`~cocotb.triggers.First` does *not* cancel Tasks that did not complete after it returns.
    This means that Tasks passed to it are *still running*.
    You may need to cancel those Tasks with :meth:`.Task.cancel`.


Determining Which Task Finishes First
-------------------------------------

:class:`~cocotb.triggers.First` can be used to determine which of multiple Tasks :meth:`complete <cocotb.task.Task.complete>` first using the following idiom.

.. code-block:: python

    @cocotb.test
    async def test_which_finished_first(dut):

        task_A = cocotb.start_soon(drive_A())
        task_B = cocotb.start_soon(drive_B())

        # Pass Task.complete rather than the Task directly.
        result = await First(task_A.complete, task_B.complete)

        # Compare the result against the Task's "complete" object.
        if result is task_A.complete:
            cocotb.log.info("Input A finished first")
        else:
            cocotb.log.info("Input B finished first")


.. _combine-tutorial:

Waiting For Multiple Events
---------------------------

:class:`~cocotb.triggers.Combine` is like awaiting multiple Triggers or Tasks at the same time,
but it resumes after *all* the listed Triggers or Tasks fire.
Using the example from the previous section, we can use it to wait until both the driving and quiesce are done.

.. code-block:: python

    @cocotb.test
    async def test_wait_for_both(dut):

        # generate stimulus and drive it to the design
        async def drive_transactions():
            for trans in generate_transactions():
                await drive(dut.intf, trans)

        # wait for both the driving and quiescing to complete before continuing
        await Combine(
            cocotb.start_soon(drive_transactions()),
            cocotb.start_soon(quiesce())
        )

And of course, the sky is the limit when you compose the two.

.. code-block:: python

    @cocotb.test
    async def test_wait_for_both_with_timeout(dut):

        # wait for both the driving and quiescing to complete before continuing
        # but timeout if *either* the driving or settling take too long
        await Combine(
            cocotb.start_soon(with_timeout(drive_transactions(), 1, "us")),
            cocotb.start_soon(with_timeout(quiesce(), 10, "us")),
        )


.. note::

    :class:`~cocotb.triggers.Combine` does *not* cancel Tasks that did not complete if it fails with an exception.
    This means that Tasks passed to it are *still running*.
    You may need to cancel those Tasks with :meth:`.Task.cancel`.


Async generators
================

Starting with Python 3.6, a :keyword:`yield` statement within an async function
has a new meaning which matches the typical meaning of yield within regular Python code.
It can be used to create a special type of generator function that can be iterated with :keyword:`async for`:

.. code-block:: python

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

.. versionchanged:: 2.0
    This style, which used the ``cocotb.coroutine`` decorator and the yield syntax, was removed.
