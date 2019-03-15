#################
Library Reference
#################

Test Results
============

The exceptions in this module can be raised at any point by any code and will terminate the test.

.. automodule:: cocotb.result
    :members:
    :member-order: bysource
    :synopsis: Exceptions and functions for simulation result handling.


Writing and Generating tests
============================

.. autoclass:: cocotb.test

.. autoclass:: cocotb.coroutine

.. autoclass:: cocotb.external

.. autoclass:: cocotb.function

.. autoclass:: cocotb.hook

.. autoclass:: cocotb.regression.TestFactory
    :members:
    :member-order: bysource


Interacting with the Simulator
==============================

.. currentmodule:: cocotb.binary

.. autoclass:: BinaryRepresentation
    :members:
    :member-order: bysource

.. autoclass:: BinaryValue
    :members:
    :member-order: bysource

.. autoclass:: cocotb.bus.Bus
    :members:
    :member-order: bysource

.. autoclass:: cocotb.clock.Clock

Triggers
--------
See :ref:`simulator-triggers` for a list of subclasses. Below are the internal
classes used within ``cocotb``.

.. currentmodule:: cocotb.triggers

.. autoclass:: Trigger
    :members:
    :member-order: bysource

.. autoclass:: GPITrigger
    :members:
    :member-order: bysource


Testbench Structure
===================

Driver
------

.. autoclass:: cocotb.drivers.Driver
    :members:
    :member-order: bysource
    :private-members:

.. autoclass:: cocotb.drivers.BitDriver
    :members:
    :member-order: bysource
    :show-inheritance:
    :private-members:

.. autoclass:: cocotb.drivers.BusDriver
    :members:
    :member-order: bysource
    :show-inheritance:
    :private-members:

.. autoclass:: cocotb.drivers.ValidatedBusDriver
    :members:
    :member-order: bysource
    :show-inheritance:
    :private-members:

Monitor
-------

.. currentmodule:: cocotb.monitors

.. autoclass:: Monitor
    :members: _monitor_recv, _recv
    :member-order: bysource
    :private-members:

    .. automethod:: wait_for_recv(timeout=None)


.. autoclass:: BusMonitor
    :members:
    :member-order: bysource
    :show-inheritance:
    :private-members:

Scoreboard
----------

.. currentmodule:: cocotb.scoreboard

.. automodule:: cocotb.scoreboard
    :members:
    :member-order: bysource
    :show-inheritance:
    :synopsis: Class for scoreboards.

Clock
-----

.. autoclass:: cocotb.clock.Clock
    :members:
    :member-order: bysource


Utilities
=========

.. automodule:: cocotb.utils
    :members:
    :member-order: bysource
    :synopsis: Various utilities for testbench writers.

Simulation Object Handles
=========================

.. currentmodule:: cocotb.handle

.. automodule:: cocotb.handle
    :members:
    :member-order: bysource
    :show-inheritance:
    :synopsis: Classes for simulation objects.

Implemented Testbench Structures
================================

Drivers
-------

AD9361
~~~~~~

Analog Devices AD9361 RF Transceiver.

.. currentmodule:: cocotb.drivers.ad9361

.. autoclass:: AD9361

    .. automethod:: send_data(i_data, q_data, i_data2=None, q_data2=None, binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT)
    .. automethod:: rx_data_to_ad9361(i_data, q_data, i_data2=None, q_data2=None, binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT)
    .. automethod:: ad9361_tx_to_rx_loopback()
    .. automethod:: tx_data_from_ad9361()


AMBA
~~~~

Advanced Microcontroller Bus Architecture.

.. currentmodule:: cocotb.drivers.amba

.. autoclass:: AXI4LiteMaster

    .. automethod:: write(address, value, byte_enable=0xf, address_latency=0, data_latency=0)
    .. automethod:: read(address, sync=True)


.. autoclass:: AXI4Slave
    :members:
    :member-order: bysource


Avalon
~~~~~~

.. currentmodule:: cocotb.drivers.avalon

.. autoclass:: AvalonMM
    :members:
    :member-order: bysource
    :show-inheritance:

.. autoclass:: AvalonMaster

    .. automethod:: write(address, value)
    .. automethod:: read(address, sync=True)


.. autoclass:: AvalonMemory
    :members:
    :member-order: bysource
    :show-inheritance:

.. autoclass:: AvalonST
    :members:
    :member-order: bysource
    :show-inheritance:

.. autoclass:: AvalonSTPkts
    :members:
    :member-order: bysource
    :show-inheritance:


OPB
~~~

.. currentmodule:: cocotb.drivers.opb

.. autoclass:: OPBMaster

    .. automethod:: write(address, value, sync=True)
    .. automethod:: read(address, sync=True)


XGMII
~~~~~

.. currentmodule:: cocotb.drivers.xgmii

.. autoclass:: XGMII
    :members:
    :member-order: bysource
    :show-inheritance:

Monitors
--------

Avalon
~~~~~~

.. currentmodule:: cocotb.monitors.avalon

.. autoclass:: AvalonST
    :members:
    :member-order: bysource
    :show-inheritance:

.. autoclass:: AvalonSTPkts
    :members:
    :member-order: bysource
    :show-inheritance:

XGMII
~~~~~

.. autoclass:: cocotb.monitors.xgmii.XGMII
    :members:
    :member-order: bysource
    :show-inheritance:
