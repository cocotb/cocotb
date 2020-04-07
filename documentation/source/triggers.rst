********
Triggers
********

Triggers are used to indicate when the cocotb scheduler should resume coroutine execution.
To use a trigger, a coroutine should :keyword:`await` it.
This will cause execution of the current coroutine to pause.
When the trigger fires, execution of the paused coroutine will resume::

.. code-block:: python3

    async def coro():
        print("Some time before the edge")
        await RisingEdge(clk)
        print("Immediately after the edge")

.. _simulator-triggers:

Simulator Triggers
==================

Signals
-------

.. autoclass:: cocotb.triggers.Edge

.. autoclass:: cocotb.triggers.RisingEdge

.. autoclass:: cocotb.triggers.FallingEdge

.. autoclass:: cocotb.triggers.ClockCycles


Timing
------

.. autoclass:: cocotb.triggers.Timer

.. autoclass:: cocotb.triggers.ReadOnly

.. autoclass:: cocotb.triggers.ReadWrite

.. autoclass:: cocotb.triggers.NextTimeStep


Python Triggers
===============

.. autoclass:: cocotb.triggers.Combine

.. autoclass:: cocotb.triggers.First

.. autoclass:: cocotb.triggers.Join
    :members: retval


Synchronization
---------------

These are not :class:`Trigger`\ s themselves, but contain methods that can be used as triggers.
These are used to synchronize coroutines with each other.

.. autoclass:: cocotb.triggers.Event
    :members:
    :member-order: bysource

.. autoclass:: cocotb.triggers.Lock
    :members:
    :member-order: bysource

.. autofunction:: cocotb.triggers.with_timeout
