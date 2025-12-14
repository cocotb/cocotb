********
Triggers
********

Triggers are used to indicate when the cocotb scheduler should resume coroutine execution.

To use a trigger, a coroutine should :keyword:`await` it.
This will cause execution of the current coroutine to pause.
When the trigger fires
(:class:`~cocotb.triggers.RisingEdge` in the following example),
execution of the paused coroutine will resume:

.. code-block:: python

    from cocotb.triggers import RisingEdge

    async def coro():
        print("Some time before a clock edge")
        await RisingEdge(clk)
        print("Immediately after the rising clock edge")


Available Triggers for Testbenches
==================================

Below is a table of triggers that are useful for writing testbenches and models.

For a list of *all* available triggers,
see the :ref:`triggers` section in the :doc:`Python Code Library Reference <library_reference>`.

..
   Please keep this table aligned with the content in library_reference.rst

+------------------------------------------+-------------------------------------------------------------------------------------------+
| **Edge Triggers**                                                                                                                    |
+------------------------------------------+-------------------------------------------------------------------------------------------+
| | :class:`~cocotb.triggers.RisingEdge`   | | Resume after a *rising* edge on a single-bit signal                                     |
| | :class:`~cocotb.triggers.FallingEdge`  | | Resume after a *falling* edge on a single-bit signal                                    |
| | :class:`~cocotb.triggers.ValueChange`  | | Resume after *any* edge on a signal                                                     |
| | :class:`~cocotb.triggers.ClockCycles`  | | Resume after the specified number of transitions of a signal                            |
| | :class:`~cocotb.triggers.Edge`         | | (deprecated, see :class:`~cocotb.triggers.ValueChange`)                                 |
+------------------------------------------+-------------------------------------------------------------------------------------------+
| **Timing Triggers**                                                                                                                  |
+------------------------------------------+-------------------------------------------------------------------------------------------+
| | :class:`~cocotb.triggers.Timer`        | | Resume after the specified time                                                         |
| | :class:`~cocotb.triggers.ReadOnly`     | | Resume when the simulation timestep moves to the *read-only* phase                      |
| | :class:`~cocotb.triggers.ReadWrite`    | | Resume when the simulation timestep moves to the *read-write* phase                     |
| | :class:`~cocotb.triggers.NextTimeStep` | | Resume when the simulation timestep moves to the *next time step*                       |
+------------------------------------------+-------------------------------------------------------------------------------------------+
| **Concurrency Triggers**                                                                                                             |
+------------------------------------------+-------------------------------------------------------------------------------------------+
| | :func:`~cocotb.triggers.gather`        | | Resume after *all* given Tasks or Triggers                                              |
| | :func:`~cocotb.triggers.select`        | | Resume after *any* given Tasks or Triggers                                              |
| | :class:`~cocotb.triggers.Combine`      | | Resume after *all* given Triggers                                                       |
| | :class:`~cocotb.triggers.First`        | | Resume after *any* given Triggers                                                       |
| | :func:`~cocotb.triggers.wait`          | | Await on all given Tasks or Triggers concurrently and block until a condition is met    |
| | :class:`~cocotb.triggers.NullTrigger`  | | Resume immediately                                                                      |
+------------------------------------------+-------------------------------------------------------------------------------------------+
| **Synchronization Triggers**                                                                                                         |
+------------------------------------------+-------------------------------------------------------------------------------------------+
| | :class:`~cocotb.triggers.Event`        | | A way to signal an event across Tasks                                                   |
| | :class:`~cocotb.triggers.Lock`         | | A mutual exclusion lock                                                                 |
| | :func:`~cocotb.triggers.with_timeout`  | | Resume latest at the specified timeout time                                             |
+------------------------------------------+-------------------------------------------------------------------------------------------+
