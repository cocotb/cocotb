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

Typically coroutines await a :class:`~cocotb.triggers.Trigger` object which
pauses the task, and indicates to the simulator some event which will cause the task to resume execution.
For example:

.. code-block:: python

    async def wait_10ns():
        cocotb.log.info("About to wait for 10 ns")
        await Timer(10, unit='ns')
        cocotb.log.info("Simulation time has advanced by 10 ns")

Coroutines may also await on other coroutines:

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
        Clock(dut.clk, 1, unit='ns').start()
        # reset_dut is a function -
        # part of the user-generated "uart_tb" class
        # run reset_dut immediately before continuing
        await tb.reset_dut(dut.rstn, 20)

        await Timer(10, unit='ns')
        print("Reset is still active: %d" % dut.rstn)
        await Timer(15, unit='ns')
        print("Reset has gone inactive: %d" % dut.rstn)

Other tasks can be used in an await statement to suspend the current task until the other task finishes.

.. code-block:: python

    @cocotb.test()
    async def test_count_edge_cycles(dut, period_ns=1, clocks=6):
        Clock(dut.clk, period_ns, unit='ns').start()
        await RisingEdge(dut.clk)

        timer = Timer(period_ns + 10, 'ns')
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
        clk_1mhz   = Clock(dut.clk, 1.0, unit='us')
        clk_250mhz = Clock(dut.clk, 4.0, unit='ns')

        clk_1mhz.start()
        start_time_ns = get_sim_time(unit='ns')
        await Timer(1, unit='ns')
        await RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(unit='ns')
        assert isclose(edge_time_ns, start_time_ns + 1000.0), "Expected a period of 1 us"

        clk_1mhz.stop()  # stop 1MHz clock here

        clk_250mhz.start()
        start_time_ns = get_sim_time(unit='ns')
        await Timer(1, unit='ns')
        await RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(unit='ns')
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

.. _task_manager_tutorial:

:class:`!TaskManager`
=====================

The :class:`~cocotb.triggers.TaskManager` class is another way to run multiple async routines concurrently and wait for them all to complete.
It properly manages the lifetime of its "children" and handles exceptions and cancellations gracefully.
Unlike :func:`gather` which takes all :term:`awaitable`\ s and :term:`coroutine`\ s at once,
:class:`!TaskManager` allows adding new :term:`!awaitable`\ s and :term:`!coroutine`\ s dynamically,
and provides options to control exception handling behavior on a per-Task basis,
making it much more flexible.

Basic Usage
-----------

To use :class:`!TaskManager`, first construct it and use it as an :term:`asynchronous context manager` with the :keyword:`async with` statement.
Inside of the context block you can use the :deco:`fork <cocotb.triggers.TaskManager.fork>` decorator method to start :class:`!Task`\ s concurrently.
When control reaches the end of the context block
the :class:`!TaskManager` blocks the encompassing :class:`!Task` until all child :class:`!Task`\ s complete.

.. code-block:: python

    from cocotb.triggers import TaskManager

    # Drive two interfaces concurrently until both complete.

    async with TaskManager() as tm:

        @tm.fork
        async def drive_interface1(): ...

        @tm.fork
        async def drive_interface2(): ...

    # Control returns here when all drive Tasks have completed

In addition to the :deco:`!fork` method for starting :term:`coroutine function`\ s concurrently,
:meth:`~cocotb.triggers.TaskManager.start_soon` can be used for :keyword:`!await`\ ing arbitrary :term:`awaitable`\ s concurrently.

.. code-block:: python

    # Wait for operation to complete or timeout after 1 us

    async with TaskManager() as tm:
        tm.start_soon(RisingEdge(cocotb.top.operation_complete))

        @tm.fork
        async def watchdog():
            await Timer(1, "us")
            raise TimeoutError("Operation did not complete in time")

Inspecting Child Task Results
-----------------------------

You can inspect the result of child classes by storing the :class:`!Task` objects returned by the :meth:`!start_soon` method.
When decoratoring a :term:`coroutine function` with :deco:`!fork`,
the name of the function will become the returned :class:`!Task` object.

.. code-block:: python

    async with TaskManager() as tm:
        task1 = tm.start_soon(RisingEdge(cocotb.top.signal_a))

        # task2 will become the Task object after wrapping the coroutine function with @fork
        @tm.fork
        async def task2():
            return 42


    assert task1.done()
    assert task1.result() is RisingEdge(cocotb.top.signal_a)

    assert task2.done()
    assert task2.result() == 42

.. note::
    After exiting the context block and the :class:`!TaskManager` has begun finishing,
    no further calls to :meth:`start_soon` or :deco:`!fork` are permitted.
    Attempting to do so will raise a :exc:`RuntimeError`.

Handling Exceptions and *continue_on_error*
-------------------------------------------

:class:`!TaskManager` gracefully handles exceptions raised in child :class:`!Task`\ s or in the context block itself.
It ensures that no child :class:`!Task` is left running unintentionally by the time the context block exits.

The behavior of :class:`!TaskManager` when a child :class:`!Task` raises an exception is controlled by the *continue_on_error* parameter.
The constructor for :class:`!TaskManager` accepts an optional parameter *continue_on_error* which is used as the default for all children Tasks;
it defaults to ``False``.
The :class:`!TaskManager`-wide default can be overridden on a per-Task basis using the *continue_on_error* parameter to the :deco:`!fork` or :meth:`!start_soon` methods.

.. code-block:: python

    async with TaskManager(continue_on_error=True) as tm:

        @tm.fork(continue_on_error=False)
        async def task1(): ...

        tm.start_soon(some_coroutine(), continue_on_error=True)

If a child :class:`!Task` raises an exception,
one of two behaviors will occur depending on the value of *continue_on_error* for that Task.
If the *continue_on_error* parameter is ``False``, all other child :class:`!Task`\ s are cancelled and the :class:`!TaskManager` will begin shutting down.
If the *continue_on_error* parameter is ``True``, the exception is captured and other child :class:`!Task`\ s are allowed to continue running.

After all child :class:`!Task`\ s have finished,
all exceptions, besides :exc:`~asyncio.CancelledError`, are gathered into an :exc:`ExceptionGroup`,
or a :exc:`BaseExceptionGroup`, if at least one of the exceptions is a :exc:`BaseException`,
and raised in the enclosing scope.

You can catch the :exc:`!ExceptionGroup` to handle errors from child :class:`!Task`\ s
by either catching the :exc:`!ExceptionGroup` as you would typically;
or, if you are running Python 3.11 or later,
using the new `except* <https://docs.python.org/3/reference/compound_stmts.html#except-star>`_ syntax
to catch specific exception types from the group.
This new syntax will run the except clause for each matching exception in the group.

.. code-block:: python

    try:
        async with TaskManager(continue_on_error=True) as tm:

            @tm.fork
            async def task1():
                ...
                raise ValueError("An error occurred in task1")

            @tm.fork
            async def task2():
                ...
                raise ValueError("An error occurred in task2")

    except* ValueError as e:
        # This will print both ValueErrors from task1 and task2
        cocotb.log.info(f"Caught ValueError from TaskManager: {e}")

.. note::
    After a :class:`!Task` fails and the :class:`!TaskManager` begins cancelling,
    no further calls to :meth:`start_soon` or :deco:`!fork` are permitted.

Failures Within the Context Block
---------------------------------

You are permitted to add any :keyword:`await` statement to the body of the context block.
This means that it is possible for child tasks to start running, and then end with an exception, before the context block has finished.
In this case, a :exc:`~asyncio.CancelledError` will be raised from the current :keyword:`!await` expression in the context block,
allowing the user to perform any necessary cleanup.
This :exc:`!CancelledError` will be squashed when the context block exits,
and :class:`!TaskManager` continues shutting down as it normally would.

.. code-block:: python

    async with TaskManager() as tm:

        @tm.fork
        async def task1():
            raise ValueError("An error occurred in task1")

        try:
            await Timer(10)  # During this await, task1 will fail
        except CancelledError:
            cocotb.log.info(
                "The rest of the context block will be skipped due to task1 failing"
            )
            raise  # DON'T FORGET THIS

        ...  # This code will be skipped

.. warning::
    Just like with :class:`~cocotb.task.Task`, if a :class:`!TaskManager` context block is cancelled
    and squashes the resulting :exc:`asyncio.CancelledError`, the test will be forcibly failed immediately.
    Always remember to re-raise the :exc:`!asyncio.CancelledError` if you catch it.

Nesting :class:`!TaskManager`
-----------------------------

:class:`!TaskManager`\ s can be arbitrarily nested.
When any child :class:`!Task` fails, the entire tree of child :class:`!Task`\ s will eventually be cancelled.

.. code-block:: python

    async with TaskManager() as tm_outer:

        @tm_outer.fork
        async def outer_task():
            ...
            raise RuntimeError("An error occurred in outer_task")

        async with TaskManager() as tm_inner:

            # This inner task will be cancelled when outer_task fails
            @tm_inner.fork
            async def another_task(): ...

    assert outer_task.exception() is RuntimeError
    assert another_task.cancelled()

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
