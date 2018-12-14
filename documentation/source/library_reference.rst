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

.. autoclass:: cocotb.hook


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
    :private-members:

Monitor
-------

.. autoclass:: cocotb.monitors.Monitor
    :members:
    :private-members:

.. autoclass:: cocotb.monitors.BusMonitor
    :members:

.. autoclass:: cocotb.scoreboard.Scoreboard
    :members:


Utilities
=========

.. automodule:: cocotb.utils
    :members:

Simulation Object Handles
=========================

.. autofunction:: cocotb.handle.SimHandle

.. autoclass:: cocotb.handle.SimHandleBase
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.RegionObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.HierarchyObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.HierarchyArrayObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.NonHierarchyObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.ConstantObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.NonHierarchyIndexableObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.NonConstantObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.ModifiableObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.RealObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.EnumObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.IntegerObject
    :members:
    :show-inheritance:

.. autoclass:: cocotb.handle.StringObject
    :members:
    :show-inheritance:

Implemented Testbench Structures
================================

Drivers
-------

AD9361
~~~~~~
.. autoclass:: cocotb.drivers.ad9361.AD9361
    :members:

AMBA
~~~~

Advanced Microcontroller Bus Archicture

.. autoclass:: cocotb.drivers.amba.AXI4LiteMaster
    :members:

.. autoclass:: cocotb.drivers.amba.AXI4LiteSlave
    :members:


Avalon
~~~~~~

.. autoclass:: cocotb.drivers.avalon.AvalonMM
    :members:

.. autoclass:: cocotb.drivers.avalon.AvalonMaster
    :members:

.. autoclass:: cocotb.drivers.avalon.AvalonMemory
    :members:

.. autoclass:: cocotb.drivers.avalon.AvalonST
    :members:

.. autoclass:: cocotb.drivers.avalon.AvalonSTPkts
    :members:

OPB
~~~

.. autoclass:: cocotb.drivers.opb.OPBMaster
    :members:

XGMII
~~~~~

.. autoclass:: cocotb.drivers.xgmii.XGMII
    :members:

Monitors
--------

Avalon
~~~~~~

.. autoclass:: cocotb.monitors.avalon.AvalonST
    :members:

.. autoclass:: cocotb.monitors.avalon.AvalonSTPkts
    :members:

XGMII
~~~~~

.. autoclass:: cocotb.monitors.xgmii.XGMII
    :members:

