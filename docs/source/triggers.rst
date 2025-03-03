********
Triggers
********

Triggers are used to indicate when the cocotb scheduler should resume coroutine execution.
To use a trigger, a coroutine should :keyword:`await` it.
This will cause execution of the current coroutine to pause.
When the trigger fires, execution of the paused coroutine will resume:

.. code-block:: python

    async def coro():
        print("Some time before a clock edge")
        await RisingEdge(clk)
        print("Immediately after the rising clock edge")

See :ref:`triggers` for a list of available triggers.
