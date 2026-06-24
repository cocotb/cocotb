############################################
Coroutines, Triggers, Tasks, and Concurrency
############################################

This document covers in greater depth the features that cocotb provides to make writing complex testbenches possible,
including the following topics:

* :term:`coroutines <coroutine>`
* :term:`triggers <trigger>`
* :term:`tasks <task>`
* :term:`concurrency`
* Running independent concurrent tasks with :func:`cocotb.start_soon`.
* Waiting for multiple things to finish with :func:`~cocotb.triggers.gather`, :func:`~cocotb.triggers.select`, and :func:`~cocotb.triggers.wait`.
* Structured concurrency with :class:`~cocotb.triggers.TaskManager`.
* Inter-task communication with :class:`~cocotb.triggers.Event` and :class:`~cocotb.queue.Queue`.
* Inter-task synchronization with :class:`~cocotb.triggers.Lock`.

What it will *not* cover is any simulation-specific or testing-specific features such as getting values from a signal, or passing and failing tests.

Now before we can get into concurrency, we need to cover the building blocks of cocotb's concurrency system,
the first being :term:`!coroutines`.

**********
Coroutines
**********

What is a coroutine?
====================

A coroutine is a special type of function that can be paused and resumed at certain points in its execution.
When a coroutine is paused, it yields control to another coroutine, allowing other code to run.
When a coroutine is resumed, it continues executing from where it left off.

If this sounds a lot like a Python generator, that's because it is.
In fact, Python's built-in :term:`coroutines <python:coroutine>` are built on top of :term:`generators <python:generator>`.

How do I define a coroutine?
============================

The main difference between regular Python functions or generators and :term:`coroutine functions <python:coroutine function>`
is that coroutine functions are defined with :keyword:`async def` instead of just :keyword:`def`.

.. code-block:: python

    async def my_coroutine():
       # This is a coroutine function because it is defined with `async def` instead of just `def`.
       # Even if there's no `await` expression in the body of the function.
       print("Hello, World!")

What makes coroutine functions useful is that they can contain :keyword:`await` expressions.
This is similar to :keyword:`yield` expressions in generators:
execution is paused at the point of the :keyword:`await` expression until the awaited object results in a value,
then execution of the coroutine resumes from the point of the :keyword:`await` expression.

.. code-block:: python

   async def my_coroutine():
       # Happens immediately.
       print("Hello")
       # This next function takes some time to complete, meanwhile this function is paused.
       await some_async_operation()
       # Happens after `some_async_operation` completes.
       print("World")

Why do I need coroutines?
=========================

Looking at the example above, you might be asking why we need coroutines at all.
It looks like it could be a regular :keyword:`!def` function and non- :keyword:`!await`\ ed function call.

There are two main reasons why we need coroutines:

1. We can :keyword:`await` things that aren't coroutines.
2. We can run multiple coroutines concurrently.

In terms of cocotb, the first point is necessary to support :keyword:`await`\ ing :term:`triggers <trigger>`,
which are not coroutines but :term:`awaitable objects <awaitable>` that represent events in the simulation.

.. code-block:: python

    @cocotb.test
    async def my_test(dut):
        await RisingEdge(dut.clk)  # awaitable...
        assert not inspect.iscoroutine(RisingEdge(dut.clk))  # but not a coroutine

We will cover cocotb's concurrency features in later sections.

Using Coroutines
================

Coroutine functions support all the same features that regular Python functions support.
They can take arguments, return values, and raise exceptions.
The only difference is that they can use :keyword:`!await` expressions while regular functions cannot.

.. note::
    That is not a license to change all your functions to coroutine functions -
    there is overhead associated with creating coroutines.

The other main difference is that coroutine functions, like generator functions, do not run the function body immediately upon calling;
nor does calling the function (without the :keyword:`!await`) block and return the function result.
Instead, calling a coroutine function returns a :term:`python:coroutine` object, which is an :term:`awaitable`.
The coroutine function's body starts only after that coroutine object is :keyword:`!await`\ ed.

.. code-block:: python
    :emphasize-lines: 9

    async def my_coroutine(arg1, arg2):
        local_var = arg1 + arg2
        if local_var > 10:
            raise ValueError("Too big!")
        return local_var

    @cocotb.test
    async def my_test(dut):
        ret = await my_coroutine(3, 4)  # ret == 7
        try:
            await my_coroutine(5, 6)
        except ValueError as e:
            assert str(e) == "Too big!"

Looking at that example, notice the :keyword:`!await` keyword appears between the assignment and the function call.
This is because :keyword:`!await` is an *expression* that takes an awaitable object.
The result of the expression is the result of the awaitable.
For coroutine functions, this means the function return value or an exception if one is raised.

To best visualize this, consider the following equivalent code below.

.. code-block:: python

    @cocotb.test
    async def my_test(dut):
        coro = my_coroutine(3, 4)
        ret = (await coro)


********************
:class:`!Trigger`\ s
********************

We mentioned earlier that one of the main reasons we need coroutines is to :keyword:`!await` things that aren't other coroutines.
In cocotb, that thing is :term:`triggers <trigger>`; they are another building block of cocotb's concurrency system.

cocotb provides triggers that represent various events in the simulation, such as a signal changing value or a certain amount of time passing.
It also provides some triggers that represent user-defined events in Python, such as an :class:`~cocotb.triggers.Event`.

For example, a :class:`RisingEdge(dut.clk) <cocotb.triggers.RisingEdge>` trigger represents the next change in value on the ``dut.clk`` signal to a ``1``.
When you :keyword:`!await` a trigger, the current coroutine is paused until the event represented by the trigger occurs in the simulation,
at which point the coroutine is resumed.

.. code-block:: python

    @cocotb.test(timeout_time=10, timeout_unit="ns")
    async def my_test(dut):
        print(get_sim_time("ns"))  # 0 ns, the start of the test.
        await RisingEdge(dut.clk)  # This coroutine is paused until the next rising edge of dut.clk.
        print(get_sim_time("ns"))  # 10 ns, the time of the rising edge of dut.clk.

A gotcha to watch out for is that if an event represented by the trigger will never occur,
then the coroutine will be paused indefinitely and your test will hang.
This is a good argument for specifying ``timeout_time`` and ``timeout_unit`` arguments to :deco:`cocotb.test` as seen above.

The only common API that all :term:`!triggers` share is that they are :term:`awaitable objects <awaitable>`.
We will be covering several particular triggers relating to concurrency later in this document,
so here is a table of the most commonly used simulation triggers which we *won't* be covering in detail in this document.

+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| **Simulator Triggers**                                                                                                                           |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+
| | :class:`~cocotb.triggers.RisingEdge`               | | Resume after a single-bit signal changes to a ``1``                                     |
| | :class:`~cocotb.triggers.FallingEdge`              | | Resume after a single-bit signal changes to a ``0``                                     |
| | :class:`~cocotb.triggers.ValueChange`              | | Resume after *any* edge on a signal                                                     |
| | :class:`~cocotb.triggers.Timer`                    | | Resume after the specified time                                                         |
| | :class:`~cocotb.triggers.ReadOnly`                 | | Resume when the simulation timestep moves to the *read-only* phase                      |
| | :class:`~cocotb.triggers.ReadWrite`                | | Resume when the simulation timestep moves to the *read-write* phase                     |
| | :class:`~cocotb.triggers.NextTimeStep`             | | Resume when the simulation timestep moves to the *next time step*                       |
+------------------------------------------------------+-------------------------------------------------------------------------------------------+


.. _concurrency_theory:

***********
Concurrency
***********

As testbenches get more complex, you will very quickly run into the need to do multiple things at the same time:

* drive inputs while monitoring outputs
* check expected results while generating stimulus
* wait indefinitely for potential error conditions while doing everything else

This is where concurrency comes in.
The following is a theoretical introduction to concurrency in general and as it pertains to cocotb.
Feel free to skip this section if you are already familiar with concurrency and just want to get to the practical details of how to use it in cocotb.

What is concurrency?
====================

Concurrency is best defined as "When multiple routines can start executing simultaneously."

This definition has the advantage of not saying "running simultaneously," which could be confusing.
This means that you can start running routine A but before A finishes running, routine B can start running.
Thus A and B are executing simultaneously.

Concurrency vs parallelism
--------------------------

Simultaneously is not the same as "in parallel."
Parallelism is a subset of concurrency.
There are forms of concurrency where two routines are executing on different execution threads of your CPU "in parallel";
and there are other forms of concurrency where only one routine is running while the others lie idle.
This is still concurrency because all of these routines have started before any have finished.

Tasks vs threads
----------------

cocotb's concurrency system is of the non-parallel form.
This means that only one routine is running at a time while the others lie idle.
Additionally, cocotb's concurrency system is cooperative,
meaning that the currently running routine must explicitly yield control before another routine can resume.

To best understand what we are dealing with, let's compare cocotb's core unit of concurrency, the :term:`task`,
to the more familiar concept of threads.

Threads are a form of parallel concurrency where multiple routines can run simultaneously on different CPU threads.
Additionally, threads are preemptive, meaning that the operating system can interrupt a running thread to allow another thread to run.
This means when you have multiple threads, you have to worry about things like race conditions caused by parallel threads contending for shared resources,
or threads being preemptively scheduled off in the middle of an operation on a shared resource leaving it in an inconsistent state.

cocotb's form of concurrency is free of these issues.
But cocotb's tasks are not free of *all* issues caused by concurrency.

It is still possible to deadlock your test.
Additionally, the scheduling order of tasks is not guaranteed to be predictable,
so you must be careful to not make assumptions about the order in which tasks will run.
Finally, because cocotb's tasks must explicitly yield control to allow other tasks to run,
you must be careful not to write a task that never yields control,
as this will starve other tasks of execution time and your testbench will hang.

Symmetric vs asymmetric concurrency
-----------------------------------

Finally, the last bit of theory we need to cover is the difference between symmetric and asymmetric concurrency.

Asymmetric concurrency is when tasks have an asymmetric relationship with other tasks,
typically this is a parent-child relationship.
In this type of concurrency multiple child tasks are spawned by a parent task,
the parent task is usually blocked upon the completion of its child tasks,
and the parent task has the right to stop the execution of any of its child tasks at any time.

An example of this would be when your test needs to wait for multiple tasks,
which drive different inputs of your design,
to complete before it can check the results of the test.

Symmetric concurrency is the opposite, where tasks have no special relationship to each other.
Symmetric tasks run independently from each other and cannot block each other.
They control their own lifetime.

An example of this would be a task which spins forever in a ``while True: ...`` loop,
waiting for a specific error condition to occur,
while the rest of the test is running.

Structured Concurrency
----------------------

Concurrency is hard to get right, so providing tools to prevent common mistakes is important.
cocotb follows the lead of other leading concurrency frameworks such as `trio <https://trio.readthedocs.io/en/stable/>`_ to provide what is called "structured concurrency."
The primary goal is to make the lifetimes of concurrent tasks easier to manage and reason about.
This prevents the common mistake of "leaking" tasks, where concurrent tasks are still running in the background when they shouldn't be.
Structured concurrency provides these guarantees lexically, so a reader can easily see the lifetime of a concurrent task just by looking at the code.

Compatibility with other concurrency frameworks
-----------------------------------------------

There are many other concurrency frameworks available in Python;
`asyncio <https://docs.python.org/3/library/asyncio.html>`_ and `trio <https://trio.readthedocs.io/en/stable/>`_ are the most popular ones.
While they all leverage Python's built-in coroutines, they are not compatible with cocotb's concurrency system.
This is because cocotb's :term:`!tasks` and :term:`!triggers` are coupled to cocotb's event loop which is fundamentally different than asyncio's or trio's.
Likewise, other concurrency frameworks have their own equivalents to tasks and triggers that are coupled to their own event loops.

You cannot use other concurrency frameworks' APIs or objects in a cocotb test,
nor can you use cocotb's tasks and triggers in other concurrency frameworks.


**************************
:func:`!cocotb.start_soon`
**************************

A typical concurrency use case in cocotb is to run a task "in the background" or "fire-and-forget,"
meaning that you want to start a task that runs concurrently and independently from the rest of the test
and let it decide on its own when to stop running (if ever) without any intervention from the rest of the test.
Examples of this include:

* The main execution thread of a Driver or Monitor.
* A concurrent assertion checker.

cocotb provides :func:`cocotb.start_soon` for this purpose.
This function takes a :term:`python:coroutine`,
wraps it into a :class:`~cocotb.task.Task`,
and runs that task concurrently and independently from the rest of the test.
The :class:`!Task` object is then returned to the caller.

.. note::
   The reason it is called "``start_soon``" is that the coroutine is only *scheduled* to start running;
   it will not start running until some time after the current task yields control.

.. code-block:: python

    async def assert_no_valid_gaps(dut):
        while True:
            await RisingEdge(dut.clk)
            assert dut.ready.value == 1 and dut.valid.value == 1

    @cocotb.test()
    async def my_test(dut):
        cocotb.start_soon(assert_no_valid_gaps(dut))
        # rest of the test

Notice the body of the ``assert_no_valid_gaps`` task is an infinite loop.
This is not a problem as long as the task yields control to allow other tasks to run.
It accomplishes this by ``await``\ ing the rising edge of the clock in each iteration of the loop.

Also notice we are not waiting for the task to end anywhere in our test.
We start it and forget about it.

Next, let's make a Driver that drives random data into an AXI-Stream-like interface continuously, as long as the ``ready`` signal is asserted.
The Driver's main execution thread (``MyDriver._run``) is started with :func:`!cocotb.start_soon`.

.. code-block:: python

    class MyDriver:
        def __init__(self, intf):
            self._intf = intf
            self._task = None

        async def _run(self):
            while True:
                self._intf.valid = 0
                self._intf.data = 0
                await RisingEdge(self._intf.clk)
                if self._intf.ready.value == 1:
                    self._intf.valid = 1
                    self._intf.data = random.randint(0, 255)

        def start(self):
            self._task = cocotb.start_soon(self._run())

Note that the :func:`!cocotb.start_soon` function returns the :class:`!Task` object that it creates.
We save that in the ``self._task`` attribute of our Driver and will use that in a later section of this document to stop the Driver's execution.

Mapping this back to our earlier discussion of symmetric vs asymmetric concurrency,
both of these are examples of symmetric concurrency.
There is no established relationship between the concurrent assert or the Driver's main thread and any other particular task.

*****************
:class:`!Task`\ s
*****************

The :class:`~cocotb.task.Task` is the final basic building block of cocotb's concurrency system.
All concurrency-oriented APIs in cocotb revolve around :class:`!Task`\ s in some way,
so understanding what they are and why they are necessary is essential to using concurrency in cocotb effectively.

Why :class:`!Task`\ s?
======================

Python coroutines only support being :keyword:`await`\ ed,
which blocks the current task until the coroutine finishes and results in the coroutine's return value.
This is a problem when we want to run multiple coroutines concurrently,
because we don't want to block the current task until the other coroutine finishes.
:class:`!Task`\ s solve this problem while also adding some additional features on top of regular coroutines, including:

* Checking the status of a Task.
* Getting the result of a Task.
* Stopping a Task's execution.

Using :class:`!Task`\ s
=======================

Just like regular Python coroutines, :keyword:`!await`\ ing a :class:`!Task` will block the current task until the task finishes and results in the Task's return value.
We can check whether a task has completed for *any* reason by calling the :meth:`~cocotb.task.Task.done` method.
We can get the result of a task with the :meth:`~cocotb.task.Task.result` method;
however, this will raise an exception if the task is not done yet, if the task raised an exception during its execution, or was cancelled.

.. code-block:: python

    async def my_coroutine():
        await Timer(10, unit="ns")
        return 42

    @cocotb.test()
    async def my_test(dut):
        task = cocotb.start_soon(my_coroutine())

        # Check if the task is still running.
        assert not task.done()

        # Wait for the task to finish and get its result.
        result = await task
        assert result == 42

        # The task is now done.
        assert task.done()

        # We can await it again, unlike Python coroutines,
        # which will finish immediately if the task is already done.
        # This often happens if there are multiple tasks waiting for the same task to finish.
        await task

        # Now that it's done, we can get the result without awaiting it.
        assert task.result() == 42


Handling Exceptions
===================

Just like regular Python coroutines, :class:`!Task`\ s can raise exceptions.
If an exception is raised in a :class:`!Task`, that exception is stored in the task and can be retrieved with the :meth:`~cocotb.task.Task.exception` method.
If you :keyword:`await` a task that has an exception, or call its :meth:`!result` method, that exception will be re-raised.

.. code-block:: python

    async def my_coroutine():
        await Timer(10, unit="ns")
        raise ValueError("Something went wrong!")

    @cocotb.test()
    async def my_test(dut):
        task = cocotb.start_soon(my_coroutine())

        # Wait for the task to finish and catch the exception.
        try:
            await task
        except ValueError as e:
            assert str(e) == "Something went wrong!"

        # The task is now done.
        assert task.done()

        # We can get the exception without awaiting it.
        assert isinstance(task.exception(), ValueError)


Cancellation and clean-up
=========================

:class:`!Task`\ s can also be cancelled.
This is done by calling the :meth:`~cocotb.task.Task.cancel` method on the task you want to cancel.
However, cancelling a task does not necessarily stop its execution immediately; the cancellation is *scheduled*.
This is because when you cancel a Task, a :exc:`~asyncio.CancelledError` exception is raised inside the Task.
We are rescheduling the task to run with that exception raised.
That :exc:`!CancelledError` exception will become the Task's result.

One final note is that calling :meth:`!result` or :meth:`!exception` on a cancelled task will raise that same :class:`~asyncio.CancelledError` exception.

.. code-block:: python

    async def my_coroutine():
        while True:
            await Timer(10, unit="ns")

    @cocotb.test()
    async def my_test(dut):
        task = cocotb.start_soon(my_coroutine())

        # Cancel the task after 50 ns.
        await Timer(50, unit="ns")
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            print("Task was cancelled!")

Now we can add some more functionality to our Driver example by adding a ``MyDriver.stop`` method that cancels the Driver's main task to stop the Driver's execution.
We are also taking advantage of the fact that cancellation raises a :exc:`!CancelledError` exception to clean up the interface when the Driver is stopped.

.. code-block:: python

    class MyDriver:
        def __init__(self, intf):
            self._intf = intf
            self._task = None

        async def _run(self):
            try:
                while True:
                    self._intf.valid = 0
                    self._intf.data = 0
                    await RisingEdge(self._intf.clk)
                    if self._intf.ready.value == 1:
                        self._intf.valid = 1
                        self._intf.data = random.randint(0, 255)
            finally:
                  # Clean up the interface when the task is cancelled.
                  # This is triggered by the CancelledError exception being raised.
                  self._intf.valid = 0
                  self._intf.data = 0

        def start(self):
            assert self._task is None, "Driver is already running!"
            self._task = cocotb.start_soon(self._run())

        def stop(self):
            assert self._task is not None, "Driver is not running!"
            # Cancel the task to stop the Driver's execution.
            self._task.cancel()
            self._task = None


***************************************************
:func:`!gather`, :func:`!select`, and :func:`!wait`
***************************************************

Another common concurrency use case you may run into is needing to wait for multiple tasks to finish before proceeding.
For specific examples:

* Waiting for multiple simultaneously executing stimulus generators to finish before finishing the test.
* Waiting for multiple testbench components to quiesce during test end.
* Timing out an operation.

cocotb provides three functions for this purpose, :func:`~cocotb.triggers.gather`, :func:`~cocotb.triggers.select`, and :func:`~cocotb.triggers.wait`.
These functions not only allow you to wait for multiple *anything* to finish,
but provide useful return values and provide cancellation and clean-up guarantees.
These cancellation and clean-up guarantees are what is meant by "structured concurrency."

:func:`!gather`
===============

:func:`~cocotb.triggers.gather` waits for all :term:`!awaitables` to complete and returns a list of their results in the same order as the :term:`!awaitables` were passed in.
If any of the :term:`!awaitables` raise an exception, that exception is propagated to the caller of :func:`!gather` and all unfinished :term:`!awaitables` are cancelled.

.. code-block:: python

    @cocotb.test()
    async def my_test(dut):
        # Wait for the design and scoreboard to quiesce before finishing the test.
        results = await gather(
            RisingEdge(dut.done),
            scoreboard.quiesce(),
        )

:func:`!select`
===============

:func:`~cocotb.triggers.select` waits for the first ``awaitable`` in its argument list to complete
and returns a tuple of the index (0-based into the argument list) of the first completed ``awaitable`` and its result.
Once the first ``awaitable`` completes, all unfinished :term:`!awaitables` are cancelled.

.. code-block:: python

    @cocotb.test()
    async def my_test(dut):
        # Ensure that the design meets the timing requirement.
        i, result = await select(
            RisingEdge(dut.condition),
            Timer(10, "us")
        )
        if i == 0:
            cocotb.log.info("Condition met!")
        else:
            cocotb.log.error("Condition not met within 10 us!")

:func:`!wait`
=============

:func:`~cocotb.triggers.wait` is the lower-level building block that :func:`!gather` and :func:`!select` are built on.
It waits for multiple :term:`!awaitables` to finish, using the keyword argument *return_when* to determine when to return.

* ``"FIRST_COMPLETED"``: Returns when the first awaitable finishes, for any reason.
* ``"FIRST_EXCEPTION"``: Returns when the first awaitable raises an exception or is cancelled, or when all complete successfully.
* ``"ALL_COMPLETED"``: Returns when all awaitables finish regardless of outcome.

:func:`!wait` returns a tuple of the index (0-based into the argument list) of the first completed awaitable or ``None`` if no *first* event occurred,
and a tuple of the waiter :class:`~cocotb.task.Task` objects.

The caller is expected to inspect these :class:`!Task`\ s with :meth:`~cocotb.task.Task.result`, :meth:`~cocotb.task.Task.exception`, and :meth:`~cocotb.task.Task.cancelled`.

Reach for :func:`!wait` when you don't want exceptions thrown to the caller, but instead want to handle them yourself.

One special use-case for :func:`!wait` over :func:`!gather` and :func:`!select` is when you want to continue execution after an exception is raised in one of the siblings.
In this case, use the ``"ALL_COMPLETED"`` return condition and inspect the returned :class:`!Task`\ s for exceptions.

.. code-block:: python

    @cocotb.test()
    async def my_test(dut):
        ...  # set up test

        _, tasks = await wait(
            sequencer_a.run(10000),
            sequencer_b.run(10000),
            check_for_data_loss(),
            return_when="ALL_COMPLETED",
        )
        if (exc := tasks[2].exception()) is not None:
            cocotb.log.error("Lost data: %r", exc)

        ...  # check other results

Composing :func:`!gather`, :func:`!select`, and :func:`!wait`
=============================================================

These functions compose with each other easily to create more complex waiting conditions,
which we can see by joining the two examples from the :func:`!gather` and :func:`!select` sections above.

.. code-block:: python

    @cocotb.test()
    async def my_test(arbitrator):
        ...  # set up test

        # Implement a timeout after 10us.
        i, res = await select(
            # Wait for scoreboard and the design to quiesce.
            gather(
                RisingEdge(dut.done),
                scoreboard.quiesce(),
            ),
            Timer(10, unit="us"),
        )
        if i == 0:
            cocotb.log.info("Design quiesced successfully!")
            # continue checking results
        else:
            raise TimeoutError("Design did not quiesce within 10 us!")

.. note::
   If you pass a :class:`Task <cocotb.task.Task>` object to :func:`!gather`, :func:`!select`, or :func:`!wait` and the call returns before that task finishes,
   the passed in task will *not* be cancelled.

.. note::
    You may be familiar with :class:`~cocotb.triggers.First` and :class:`~cocotb.triggers.Combine` which can also be used to wait for multiple things,
    but they are limited to waiting for :term:`triggers <trigger>` only, not :term:`coroutines <coroutine>` or other :term:`!awaitables`.

    This often forces the user to use :func:`cocotb.start_soon` and manage task lifetimes themselves
    which is verbose and rarely done correctly leading to :term:`!tasks` "leaking".

    They also do not return useful results like :func:`!gather`, :func:`!select`, and :func:`!wait` do.

    For those reasons they are no longer recommended except for passing to functions or objects where specifically :term:`!triggers` are expected.


.. _task_manager_tutorial:

*********************
:class:`!TaskManager`
*********************

The :class:`~cocotb.triggers.TaskManager` class is another way to run multiple async routines concurrently and wait for them all to complete.
It properly manages the lifetime of its "children" and handles exceptions and cancellations gracefully.
Unlike :func:`~cocotb.triggers.gather` which takes all :term:`awaitable`\ s and :term:`coroutine`\ s at once,
:class:`!TaskManager` allows adding new :term:`!awaitable`\ s and :term:`!coroutine`\ s dynamically,
and provides options to control exception handling behavior on a per-Task basis,
making it much more flexible.

Basic Usage
===========

To use :class:`!TaskManager`, first construct it and use it as an :term:`asynchronous context manager` with the :keyword:`async with` statement.
Inside the context block you can use the :deco:`fork <cocotb.triggers.TaskManager.fork>` decorator method to start :class:`Task <cocotb.task.Task>`\ s concurrently.
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

In addition to the :deco:`!fork` method for starting :term:`coroutine functions <coroutine function>` concurrently,
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
=============================

You can inspect the result of child tasks by storing the :class:`!Task` objects returned by the :meth:`!start_soon` method.
When decorating a :term:`coroutine function` with :deco:`!fork`,
the name of the function will become the returned :class:`!Task` object.

.. code-block:: python

    async with TaskManager() as tm:
        task1 = tm.start_soon(RisingEdge(cocotb.top.signal_a))

        # task2 will become the task object after wrapping the coroutine function with @fork
        @tm.fork
        async def task2():
            return 42


    assert task1.done()
    assert task1.result() is RisingEdge(cocotb.top.signal_a)

    assert task2.done()
    assert task2.result() == 42

.. note::
    After exiting the context block and the :class:`!TaskManager` has begun finishing,
    no further calls to :meth:`!start_soon` or :deco:`!fork` are permitted.
    Attempting to do so will raise a :exc:`RuntimeError`.

Handling Exceptions and ``continue_on_error``
=============================================

:class:`!TaskManager` gracefully handles exceptions raised in child :class:`!Task`\ s or in the context block itself.
It ensures that no child :class:`!Task` is left running unintentionally by the time the context block exits.

The behavior of :class:`!TaskManager` when a child :class:`!Task` raises an exception is controlled by the ``continue_on_error`` parameter.
The constructor for :class:`!TaskManager` accepts an optional parameter *default_continue_on_error* which is used as the default for all child tasks;
it defaults to ``False``.
The :class:`!TaskManager`-wide default can be overridden on a per-Task basis using the ``continue_on_error`` parameter to the :deco:`!fork` or :meth:`!start_soon` methods.

.. code-block:: python

    async with TaskManager(default_continue_on_error=True) as tm:

        @tm.fork(continue_on_error=False)
        async def task1(): ...

        tm.start_soon(some_coroutine(), continue_on_error=True)

If a child :class:`!Task` raises an exception,
one of two behaviors will occur depending on the value of ``continue_on_error`` for that Task.
If the ``continue_on_error`` parameter is ``False``, all other child :class:`!Task`\ s are cancelled and the :class:`!TaskManager` will begin shutting down.
If the ``continue_on_error`` parameter is ``True``, the exception is captured and other child :class:`!Task`\ s are allowed to continue running.

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
        async with TaskManager(default_continue_on_error=True) as tm:

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
    no further calls to :meth:`!start_soon` or :deco:`!fork` are permitted.
    Attempting to do so will raise a :exc:`RuntimeError`.

Failures Within the Context Block
=================================

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
            await Timer(10, unit="ns")  # During this await, task1 will fail
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

A context block can also fail with an exception like a child :class:`!Task` could.
In this case, if the *context_continue_on_error* parameter to the constructor is ``False``, all child :class:`!Task`\ s are cancelled;
if it is set to ``True``, other child :class:`!Task`\ s are allowed to continue running.
In either case, after all child :class:`!Task`\ s have finished,
all exceptions, besides :exc:`~asyncio.CancelledError`, are gathered into an :exc:`ExceptionGroup`,
or a :exc:`BaseExceptionGroup`, if at least one of the exceptions is a :exc:`BaseException`,
and raised in the enclosing scope.

.. code-block:: python

    try:
        async with TaskManager(context_continue_on_error=True) as tm:

            @tm.fork
            async def task1():
                ...
                return 42

            raise ValueError("An error occurred in the context block")

    except* ValueError as e:
        # This will print the ValueError from the context block
        cocotb.log.info(f"Caught ValueError from TaskManager: {e}")

    assert task1.result() == 42  # task1 was allowed to continue running until completion

Nesting :class:`!TaskManager`
=============================

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

.. note::
    Prefer using :func:`!gather` and :func:`!select` when possible as they are more readable for the cases they can cover.


********************************************
Synchronization and Inter-Task Communication
********************************************

What we've covered in the past few sections mostly deals with asymmetric concurrency:
parent tasks spawning multiple independent child tasks and waiting for them to finish.
However, it is common for multiple independent :term:`!tasks` to need to communicate or coordinate with each other.
For example:

* A Driver running concurrently needs stimulus that's generated by another task or the test.
* Multiple tasks need to share access to a shared resource like a register bus.
* The test needs to know when a stimulus generator has finished or a scoreboard has quiesced.

cocotb provides several APIs for inter-task communication and synchronization, including:

* :class:`~cocotb.triggers.Event` for notifying waiters that some event has occurred.
* :class:`~cocotb.queue.Queue` for passing messages between tasks.
* :class:`~cocotb.triggers.Lock` for ensuring exclusive access to a shared resource.

Let's go through each of these in turn.

:class:`!Event`
===============

An :class:`~cocotb.triggers.Event` allows one or more tasks to wait for an event to occur.
Waiting is done by :keyword:`!await`\ ing :meth:`.Event.wait`, which blocks until the Event is set.
The Event is set by calling :meth:`.Event.set`, which wakes up all tasks that are waiting on that Event.

:class:`!Event`\ s are stateful;
after an Event is set, any future calls to :meth:`.Event.wait` will not block.
You can check to see if the Event is in the "set" state with :meth:`.Event.is_set`
and put the Event back into the "unset" state with :meth:`.Event.clear`.

.. code-block:: python

    from cocotb.triggers import Event, with_timeout

    class Checker:
        """Checks expected vs actual in order of arrival. Assumes expecteds arrive before actuals."""

        def __init__(self):
            self._quiesced = Event()
            self._expected_queue = []

        def add_expected(self, expected):
            self._expected_queue.append(expected)
            self._quiesced.clear()  # Not quiesced if there's an expected waiting to be checked.

        def add_actual(self, actual):
            expected = self._expected_queue.pop(0)
            assert actual == expected
            if not self._expected_queue:
                self._quiesced.set()  # Quiesced if there are no more expecteds waiting to be checked.

    @cocotb.test
    async def my_test(dut):
        checker = Checker()

        ...  # set up drivers and run stimulus

        # Wait for all expecteds to be checked.
        await with_timeout(
                checker._quiesced.wait(),
                timeout_time=100,
                timeout_unit="us",
        )

:class:`!Queue`
===============

A :class:`~cocotb.queue.Queue` is a first-in-first-out (FIFO) queue with built-in synchronization,
somewhat similar to a Mailbox in UVM,
and very similar to :class:`asyncio.Queue` in the Python standard library.
It supports multiple producers and consumers,
and allows producers and consumers to wait for items to be added or removed from the queue as necessary.

There are two interfaces to a :class:`!Queue`, a blocking interface with :meth:`~cocotb.queue.Queue.put` and :meth:`~cocotb.queue.Queue.get`,
and a non-blocking interface with :meth:`~cocotb.queue.Queue.put_nowait` and :meth:`~cocotb.queue.Queue.get_nowait`.

Each :class:`!Queue` has a maximum size, which is infinite by default.
If a producer tries to add an item to a full queue, it will block until there is space in the queue (:func:`!put`) or raise an exception  (:func:`!put_nowait`).
If a consumer tries to remove an item from an empty queue, it will block until there is an item in the queue (:func:`!get`) or raise an exception  (:func:`!get_nowait`).

A common use case might be a Driver, which runs in an independent task, that needs stimulus from the test or some other task.
Going back to our earlier Driver example, we can modify it to take stimulus from a :class:`!Queue` instead of generating it randomly.

.. code-block:: python

    from cocotb.queue import Queue

    class MyDriver:
        def __init__(self, intf):
            self._intf = intf
            self._task = None
            self._queue = Queue()

        async def _run(self):
            while True:
                # Default values when there's no stimulus to send.
                self._intf.valid = 0
                self._intf.data = 0

                # Blocks the Driver in the idle state until there is stimulus to send.
                data = await self._queue.get()

                # Synchronize.
                await RisingEdge(self._intf.clk)

                # Write the data.
                self._intf.valid = 1
                self._intf.data = data

                # Wait for ready to go high to ensure the transaction is accepted.
                while self._intf.ready.value != 1:
                    await RisingEdge(self._intf.clk)

        def add_transaction(self, data):
            # Add stimulus to the queue without blocking.
            # Since the Queue is unbounded, this will never raise an exception.
            self._queue.put_nowait(data)

        ...  # start and stop methods omitted for brevity

    @cocotb.test
    async def my_test(dut):
        driver = MyDriver(dut.input)


:class:`!Lock`
==============

The final synchronization primitive that cocotb provides is :class:`~cocotb.triggers.Lock`.
This is a mutual exclusion lock similar to :class:`asyncio.Lock` in the Python standard library.

A :class:`!Lock` has two states, "locked" and "unlocked."
When a :class:`!Lock` is locked, any task that tries to acquire the lock will block until the lock is unlocked.
When a :class:`!Lock` is unlocked, any task can acquire the lock, which will change its state to locked.

The methods :meth:`.Lock.acquire` and :meth:`~cocotb.triggers.Lock.release` are used to acquire and release the lock, respectively.
However, it is recommended to use :class:`!Lock` as an asynchronous context manager with :keyword:`async with`,
which will automatically acquire the lock at the beginning of the block and release it at the end of the block, even if an exception is raised.

A common use case is to gate access to a shared resource like a register bus.
You may have multiple tasks that need to read registers for checking purposes,
or poll a register for a condition to be met,
or to write registers for configuration purposes.
To prevent collisions, a :class:`!Lock` should be used.
Below we wrap a register bus interface in a class that uses a :class:`!Lock` to ensure only one transaction can be happening at a time.

.. code-block:: python

    from enum import IntEnum

    from cocotb.triggers import RisingEdge, Lock

    class RequestType(IntEnum):
        IDLE = 0
        READ = 1
        WRITE = 2

    class RegisterBus:
        def __init__(self, intf):
            self._intf = intf
            # The mutual exclusion lock.
            self._lock = Lock()

        async def read(self, addr):
            # Acquire the lock.
            async with self._lock:

                # Perform the read transaction on the interface.
                self._intf.addr = addr
                self._intf.request = RequestType.READ
                await RisingEdge(self._intf.clk)
                self._intf.request = RequestType.IDLE
                while self._intf.complete.value != 1:
                    await RisingEdge(self._intf.clk)
                return self._intf.data.value

            # Lock automatically released.

        async def write(self, addr, data):
            # Acquire the lock.
            async with self._lock:

                # Perform the write transaction on the interface.
                self._intf.addr = addr
                self._intf.data = data
                self._intf.request = RequestType.WRITE
                await RisingEdge(self._intf.clk)
                self._intf.request = RequestType.IDLE
                while self._intf.complete.value != 1:
                    await RisingEdge(self._intf.clk)

            # Lock automatically released.


****************
Async generators
****************

One final coroutine feature that Python provides that is worth mentioning is the :term:`async generator`.
They are conceptually similar to regular Python generators,
and use the same :keyword:`yield` syntax to send values back to the caller,
but they also support :keyword:`await`\ ing in their body like regular Python :term:`coroutines <python:coroutine>`.
Iteration over :term:`!async generators` is done with :keyword:`async for`:

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
