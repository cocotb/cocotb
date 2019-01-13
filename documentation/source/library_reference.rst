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

.. autoclass:: cocotb.clock.Clock


Triggers
--------

Triggers are used to indicate when the scheduler should resume `coroutine` execution.  Typically a `coroutine` will **yield** a trigger or a list of triggers.

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

Driver
------

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

Scoreboard
----------

.. autoclass:: cocotb.scoreboard.Scoreboard
    :members:

Clock
-----

.. autoclass:: cocotb.clock.Clock
    :members:

Implemented Testbench Structures
================================

Drivers
-------

AD9361
~~~~~~

.. currentmodule:: cocotb.drivers.ad9361

.. autoclass:: AD9361

    .. automethod:: send_data(i_data, q_data, i_data2=None, q_data2=None, binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT)
    .. automethod:: rx_data_to_ad9361(i_data, q_data, i_data2=None, q_data2=None, binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT)
    .. automethod:: ad9361_tx_to_rx_loopback()
    .. automethod:: tx_data_from_ad9361()

    :members:

AMBA
~~~~

Advanced Microcontroller Bus Archicture

.. currentmodule:: cocotb.drivers.amba

.. autoclass:: AXI4LiteMaster

    .. automethod:: write(address, value, byte_enable=0xf, address_latency=0, data_latency=0)
    .. automethod:: read(address, sync=True)

    :members:

.. autoclass:: AXI4Slave
    :members:


Avalon
~~~~~~

.. currentmodule:: cocotb.drivers.avalon

.. autoclass:: AvalonMM
    :members:

.. autoclass:: AvalonMaster
               
    .. automethod:: write(address, value)
    .. automethod:: read(address, sync=True)
                    
    :members:

.. autoclass:: AvalonMemory
    :members:

.. autoclass:: AvalonST
    :members:

.. autoclass:: AvalonSTPkts
    :members:

OPB
~~~

.. currentmodule:: cocotb.drivers.opb
                   
.. autoclass:: OPBMaster
               
    .. automethod:: write(address, value, sync=True)
    .. automethod:: read(address, sync=True)
                    
    :members:

XGMII
~~~~~

.. currentmodule:: cocotb.drivers.xgmii

.. autoclass:: XGMII
    :members:

Monitors
--------

Avalon
~~~~~~

.. currentmodule:: cocotb.monitors.avalon

.. autoclass:: AvalonST
    :members:

.. autoclass:: AvalonSTPkts
    :members:

XGMII
~~~~~

.. autoclass:: cocotb.monitors.xgmii.XGMII
    :members:

Utilities
=========

.. automodule:: cocotb.utils
    :members:

Simulation Object Handles
=========================

.. currentmodule:: cocotb.handle

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

