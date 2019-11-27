Triggers
========

Triggers are used to indicate when the cocotb scheduler should resume coroutine execution.
To use a trigger, a coroutine should :keyword:`await` or :keyword:`yield` it.
This will cause execution of the current coroutine to pause.
When the trigger fires, execution of the paused coroutine will resume::

    @cocotb.coroutine
    def coro():
        print("Some time before the edge")
        yield RisingEdge(clk)
        print("Immediately after the edge")

Or using the syntax in Python 3.5 onwards:

.. code-block:: python3

    @cocotb.coroutine
    async def coro():
        print("Some time before the edge")
        await RisingEdge(clk)
        print("Immediately after the edge")

.. _simulator-triggers:

Simulator Triggers
------------------

Signals
~~~~~~~

.. autoclass:: cocotb.triggers.Edge

.. autoclass:: cocotb.triggers.RisingEdge

.. autoclass:: cocotb.triggers.FallingEdge

.. autoclass:: cocotb.triggers.ClockCycles

.. autoclass:: cocotb.triggers.StableCondition

.. autoclass:: cocotb.triggers.StableValue


Timing
~~~~~~

.. autoclass:: cocotb.triggers.Timer

.. autoclass:: cocotb.triggers.ReadOnly

.. autoclass:: cocotb.triggers.ReadWrite

.. autoclass:: cocotb.triggers.NextTimeStep


Python Triggers
---------------

.. autoclass:: cocotb.triggers.Combine

.. autoclass:: cocotb.triggers.First

.. autoclass:: cocotb.triggers.Join
    :members: retval


Synchronization
~~~~~~~~~~~~~~~

These are not :class:`Trigger`\ s themselves, but contain methods that can be used as triggers.
These are used to synchronize coroutines with each other.

.. autoclass:: cocotb.triggers.Event
    :members:
    :member-order: bysource

.. autoclass:: cocotb.triggers.Lock
    :members:
    :member-order: bysource
