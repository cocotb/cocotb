****************
The Timing Model
****************

cocotb's timing model is a simplification of the :term:`VPI`\ 's, :term:`VHPI`\ 's, and :term:`FLI`\ 's timing model,
made by choosing the common subset of the most important aspects of those timing models.

Like the aforementioned timing models, cocotb's is organized around :term:`time steps <time step>`.
A time step is a single point in simulated time,
comprised of one or more :term:`evaluation cycles <evaluation cycle>`.
For example, there is a time step that occurs on a rising clock edge, and the next time step is typically on the falling clock edge.
Moving between time steps will advance simulated time.

Evaluation cycles occur when HDL or cocotb code is executed in reaction to events,
such as simulated time advancing or a signal or variable changing value.
The executed code tends to create more events, leading to the next evaluation cycle.
Evaluation cycles don't advance simulated time.

cocotb provides Python timing :term:`triggers <trigger>` allowing users to move through time steps and evaluation cycles.
:keyword:`await`\ ing these triggers will cause the current cocotb coroutine to block until simulation reaches the specific point in time.

The Time Step
=============

Time steps are split into five phases in the cocotb timing model,
some of which are repeated many times.

The time step starts in the :ref:`beginning-of-time-step` (BOTS) phase and ends in the :ref:`end-of-time-step` (EOTS) phase.
Evaluation cycles occur between these two points,
with the simulator running in the :ref:`evaluation` phases,
and cocotb code reacting in the :ref:`values-change` and :ref:`values-settle` phases.

.. image:: diagrams/svg/timing_model.svg


.. _beginning-of-time-step:

Beginning of Time Step
----------------------

This is the phase where the :class:`.NextTimeStep` and :class:`.Timer` triggers will return.
This phase begins the time step before any HDL code has executed or any signal or variable have changed value.
In this phase, users are allowed to read and write any signal or variable.
Once control returns to the simulator, it will enter the :ref:`evaluation` phase.

Users can :keyword:`await` the following triggers in this phase:

* :class:`.NextTimeStep` to move to the :ref:`beginning of the next time step <beginning-of-time-step>`.
* :class:`.Timer` to move to the :ref:`beginning of any following time step <beginning-of-time-step>`.
* :class:`.ValueChange`, :class:`.RisingEdge` or :class:`.FallingEdge` to move to the next :ref:`values-change` phase where the requested value changes.
* :class:`.ReadWrite` to move to the :ref:`end of the first evaluation cycle <values-settle>`.
* :class:`.ReadOnly` to move to the :ref:`end of the current time step <end-of-time-step>`.

.. _evaluation:

HDL Evaluation
--------------

This phase represents the time spent in the simulator evaluating ``always`` or ``process`` blocks, continuous assignments, or other HDL code.
If a signal or variable passed to a :class:`.ValueChange`, :class:`.RisingEdge`, or :class:`.FallingEdge` trigger changes value accordingly,
the simulator will enter the :ref:`values-change` phase.
Alternatively, after all values have changed and all HDL has finished executing,
it will enter the :ref:`values-settle` phase.

.. note::
    cocotb is not executing during this phase, so no triggers can be :keyword:`await`\ ed.

.. _values-change:

Values Change
-------------

This is the phase where the :class:`.ValueChange`, :class:`.RisingEdge`, or :class:`.FallingEdge` triggers will return.
The signal or variable given to the trigger will have changed value,
but no HDL that reacts to that value change will have executed;
meaning "downstream" signals and variables will not have updated values.
In this phase, users can read and write values on any signal or variable.
After control returns to the simulator, it will re-enter the :ref:`evaluation` phase.

There are 0 or more of these phases in a time step and they are not distinguishable from cocotb.
There is no way to jump to any particular one of these phases in a time step.

Users can :keyword:`await` the following triggers in this phase:

* :class:`.NextTimeStep` to move to the :ref:`beginning of the next time step <beginning-of-time-step>`.
* :class:`.Timer` to move to the :ref:`beginning of any following time step <beginning-of-time-step>`.
* :class:`.ValueChange`, :class:`.RisingEdge`, or :class:`.FallingEdge` to move to the next :ref:`values-change` phase where the requested value changes.
* :class:`.ReadWrite` to move to the :ref:`end of the current evaluation cycle <values-settle>`.
* :class:`.ReadOnly` to move to the :ref:`end of the current time step <end-of-time-step>`.

.. _values-settle:

Values Settle
-------------

This is the phase where the :class:`.ReadWrite` trigger will return.
All signals and variables will have their final values and all HDL will have executed for the time step.
In this phase, users can read and write values on any signal or variable.
If they do write, the simulator will re-enter the :ref:`evaluation` phase.
Alternatively, the simulator will enter the :ref:`end-of-time-step` phase.

There are 0 or more of these phases in a time step and they are not distinguishable from cocotb.
There is no way to jump to any particular one of these phases in a time step.

Users can :keyword:`await` the following triggers in this phase:

* :class:`.NextTimeStep` to move to the :ref:`beginning of the next time step <beginning-of-time-step>`.
* :class:`.Timer` to move to the :ref:`beginning of any following time step <beginning-of-time-step>`.
* :class:`.ValueChange`, :class:`.RisingEdge`, or :class:`.FallingEdge` to move to the next :ref:`values-change` phase where the requested value changes.
* :class:`.ReadWrite` to move to the :ref:`end of the next evaluation cycle <values-settle>`.
* :class:`.ReadOnly` to move to the :ref:`end of the current time step <end-of-time-step>`.

.. _end-of-time-step:

End of Time Step
----------------

This is the phase where the :class:`.ReadOnly` trigger will return.
All signals and variables will have their final values and all HDL will have executed for the time step.
However, unlike the :ref:`values-settle` phase, no writes are allowed in this phase;
meaning no new evaluation cycles can occur.
Users can still freely read in this phase.
Once control returns to the simulator, it will move to the :ref:`beginning of the next time step <beginning-of-time-step>`.

Users can :keyword:`await` the following triggers in this phase:

* :class:`.NextTimeStep` to move to the :ref:`beginning of the next time step <beginning-of-time-step>`.
* :class:`.Timer` to move to the :ref:`beginning of any following time step <beginning-of-time-step>`.
* :class:`.ValueChange`, :class:`.RisingEdge`, or :class:`.FallingEdge` to move to the next :ref:`values-change` phase where the requested value changes.

.. note::
    :class:`await ReadWrite() <cocotb.triggers.ReadWrite>` or :class:`await ReadOnly() <cocotb.triggers.ReadOnly>`
    in this phase **are not** well defined behaviors and will result in a :exc:`RuntimeError` being raised.


Triggers
========

:class:`.Timer`
---------------

The :class:`.Timer` trigger allows users to jump forward in simulated time arbitrarily.
It will always return at the :ref:`beginning of time step <beginning-of-time-step>`.
Simulated time cannot move backwards, meaning negative and ``0`` time values are not valid.
:class:`.Timer` cannot be used to move between evaluation cycles, only between time steps.

:class:`.NextTimeStep`
----------------------

:class:`.NextTimeStep` is like :class:`.Timer`,
except that it always returns at the :ref:`beginning of the next time step <beginning-of-time-step>`.
The next time step could be at any simulated time thereafter, **or never**.
It is only safe to use if there is scheduled behavior that will cause another time step to occur.
Using :class:`.NextTimeStep` in other situations will result in undefined behavior.

:class:`.ValueChange` / :class:`.RisingEdge` / :class:`.FallingEdge`
--------------------------------------------------------------------

The edge triggers (:class:`.ValueChange`, :class:`.RisingEdge`, and :class:`.FallingEdge`)
allow users to block a cocotb coroutine until a signal or variable changes value at some point in the future.
That point in the future may be in a different evaluation cycle in the same time step, in a different time step, **or never**.
Using an edge trigger on a signal or variable that will never change value will result in undefined behavior.

After returning, an edge trigger returns at the point where the signal or variable given to the trigger will have changed value,
but no HDL that reacts to that value change will have executed;
meaning "downstream" signals and variables will not have updated values.

Using a flip-flop for example, after an ``await RisingEdge(dut.clk)``, ``dut.clk`` will be ``1``,
but the output of the flip-flop will remain the previous value.
Wait until :class:`.ReadWrite` or :class:`.ReadOnly` to see the output change.

:class:`.ReadWrite`
-------------------

:class:`.ReadWrite` allows users to synchronize with the :ref:`end of the current evaluation cycle <values-settle>`.
At the end of the evaluation cycle, all signals and variables will have their final values and all HDL will have executed for the time step.
However, users are still allowed to write.
This can be useful when trying to react combinationally to a registered signal.

For example, to set ``dut.valid`` high in reaction to ``dut.ready`` going high as a combinational circuit would,
users could write the following.

.. code-block:: python

    while True:
        await RisingEdge(dut.clk)
        await ReadWrite()
        dut.valid.value = 0
        if dut.ready.value == 1:
            dut.valid.value = 1


:class:`.ReadOnly`
------------------

:class:`.ReadOnly` allows users to jump to the :ref:`end of the time step <end-of-time-step>`;
allowing them to read the final values of signals or variables before more simulated time is consumed.
This may be necessary if they wish to sample a signal or variable whose value glitches (changes value in multiple evaluation cycles).

.. note::
    :class:`await ReadWrite() <cocotb.triggers.ReadWrite>` or :class:`await ReadOnly() <cocotb.triggers.ReadOnly>`
    after an ``await ReadOnly()`` **is not** well defined and will result in a :exc:`RuntimeError` being raised.


State Transitions
=================

.. parsed-literal::

    N := time step
    M := evaluation cycle

    BEGIN{N} ->
        BEGIN{>N} : Timer
        BEGIN{N+1} : NextTimeStep
        CHANGE{N,>=0} : ValueChange/RisingEdge/FallingEdge
        CHANGE{>N,>=0} : ValueChange/RisingEdge/FallingEdge
        SETTLE{N,0} : ReadWrite
        END{N} : ReadOnly

    CHANGE{N,M} ->
        BEGIN{>N} : Timer
        BEGIN{N+1} : NextTimeStep
        CHANGE{N,>M} : ValueChange/RisingEdge/FallingEdge
        CHANGE{>N,>=0} : ValueChange/RisingEdge/FallingEdge
        SETTLE{N,M} : ReadWrite
        END{N} : ReadOnly

    SETTLE{N,M} ->
        BEGIN{>N} : Timer
        BEGIN{N+1} : NextTimeStep
        CHANGE{N,>M} : ValueChange/RisingEdge/FallingEdge
        CHANGE{>N,>=0} : ValueChange/RisingEdge/FallingEdge
        SETTLE{N,M+1} : ReadWrite
        END{N} : ReadOnly

    END{N} ->
        BEGIN{>N} : Timer
        BEGIN{N+1} : NextTimeStep


Differences in Verilator
========================

Verilator is a cycle-based simulator, meaning it does not have discrete events like "value changed."
Instead it has "cycles", meaning it evaluates all HDL code in a time step iteratively until quiescence, without stopping.
This frees the simulator to evaluate the HDL however it sees fit, as long as it can maintain correctness, allowing for optimizations.

In Verilator, the :class:`.Timer`, :class:`.NextTimeStep`, :class:`.ReadWrite`, and :class:`.ReadOnly` work as intended, as these map to "cycles" well.
However, the value change triggers: :class:`.ValueChange`, :class:`.RisingEdge`, and :class:`.FallingEdge`, can not be handled in the middle of a cycle,
so they are handled after the cycle has ended (equivalent to the :class:`.ReadWrite` phase).
The easiest way to think of the behavior is as if the value change triggers all have an implicit ``await ReadWrite()`` after them.
