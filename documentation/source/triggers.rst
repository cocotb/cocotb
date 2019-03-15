Triggers
========

Triggers are used to indicate when the cocotb scheduler should resume coroutine execution.
Typically a coroutine will :keyword:`yield` a trigger or a list of triggers,
while it is waiting for them to complete. 

Simulation Timing
-----------------

:class:`Timer(time) <.Timer()>`:
    Registers a timed callback with the simulator to continue execution of the coroutine
    after a specified simulation time period has elapsed.


:class:`.ReadOnly()`:
    Registers a callback which will continue execution of the coroutine when the current simulation timestep moves to the :any:`ReadOnly` phase of the RTL simulator.
    The :any:`ReadOnly` phase is entered when the current timestep no longer has any further delta steps.
    This should be a point where all the signal values are stable as there are no more RTL events scheduled for the timestep.
    The simulator should not allow scheduling of more events in this timestep.
    Useful for monitors which need to wait for all processes to execute (both RTL and cocotb) to ensure sampled signal values are final.


Signal related
--------------

:class:`Edge(signal) <.Edge()>`:
    Registers a callback that will continue execution of the coroutine on any value change of *signal*.

:class:`RisingEdge(signal) <.RisingEdge()>`:
    Registers a callback that will continue execution of the coroutine on a transition from ``0`` to ``1`` of *signal*.

:class:`FallingEdge(signal) <.FallingEdge()>`:
    Registers a callback that will continue execution of the coroutine on a transition from ``1`` to ``0`` of *signal*.

:class:`ClockCycles(signal, num_cycles) <.ClockCycles>`:
    Registers a callback that will continue execution of the coroutine when *num_cycles* transitions from ``0`` to ``1`` have occured on *signal*.


Python Triggers
---------------

:class:`.Event()`:
    Can be used to synchronise between coroutines.
    Yielding :meth:`.Event.wait()` will block the coroutine until :meth:`.Event.set()` is called somewhere else.

:class:`Join(coroutine_2) <.Join()>`:
    Will block the coroutine until *coroutine_2* has completed.
