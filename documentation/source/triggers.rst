Triggers
========

Triggers are used to indicate when the scheduler should resume coroutine execution.  Typically a coroutine will **yield** a trigger or a list of triggers.

Simulation Timing
-----------------

Timer(time)
^^^^^^^^^^^

Registers a timed callback with the simulator to continue execution of the coroutine after a specified simulation time period has elapsed.

.. todo::
   What is the behaviour if time=0?


ReadOnly()
^^^^^^^^^^

Registers a callback which will continue execution of the coroutine when the current simulation timestep moves to the ReadOnly phase.  Useful for monitors which need to wait for all processes to execute (both RTL and cocotb) to ensure sampled signal values are final.



Signal related
--------------

Edge(signal)
^^^^^^^^^^^^

Registers a callback that will continue execution of the coroutine on any value change of a signal.

.. todo::
   Behaviour for vectors


RisingEdge(signal)
^^^^^^^^^^^^^^^^^^

Registers a callback that will continue execution of the coroutine on a transition from 0 to 1 of signal.


FallingEdge(signal)
^^^^^^^^^^^^^^^^^^

Registers a callback that will continue execution of the coroutine on a transition from 1 to 0 of signal.


ClockCycles(signal, num_cycles)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Registers a callback that will continue execution of the coroutine when num_cycles transistions from 0 to 1 have occured.


Python Triggers
---------------

Event()
^^^^^^^

Can be used to synchronise between coroutines. yielding Event.wait() will block the coroutine until Event.set() is called somewhere else.



Join(coroutine)
^^^^^^^^^^^^^^^

Will block the coroutine until another coroutine has completed.


