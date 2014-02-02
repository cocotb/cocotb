#################
Library Reference
#################

Test Results
============

The following exceptions can be raised at any point by any code and will terminate the test:

.. autoclass:: cocotb.result.TestComplete

.. autoclass:: cocotb.result.TestError

.. autoclass:: cocotb.result.TestFailure

.. autoclass:: cocotb.result.TestSuccess


Writing and Generating tests
============================

.. autoclass:: cocotb.test

.. autoclass:: cocotb.coroutine

.. autoclass:: cocotb.regression.TestFactory
    :members:



Interacting with the Simulator
==============================


.. autoclass:: cocotb.binary.BinaryValue
    :members:

.. autoclass:: cocotb.bus.Bus
    :members:


Triggers
--------

Triggers are used to indicate when the scheduler should resume coroutine execution.  Typically a coroutine will **yield** a trigger or a list of triggers.

Simulation Timing
~~~~~~~~~~~~~~~~~

.. autoclass:: cocotb.triggers.Timer

.. autoclass:: cocotb.triggers.ReadOnly


Signal related
~~~~~~~~~~~~~~

.. autoclass:: cocotb.triggers.Edge

.. autoclass:: cocotb.triggers.RisingEdge


Python Triggers
~~~~~~~~~~~~~~~


.. autoclass:: cocotb.triggers.Event
    :members:

.. autoclass:: cocotb.triggers.Lock
    :members:

.. autoclass:: cocotb.triggers.Join
    :members:


Testbench Structure
===================

.. autoclass:: cocotb.drivers.Driver
    :members:

.. autoclass:: cocotb.monitors.Monitor
    :members:

.. autoclass:: cocotb.scoreboard.Scoreboard
    :members:



