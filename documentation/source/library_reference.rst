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

.. autofunction:: cocotb.fork

.. autofunction:: cocotb.decorators.RunningCoroutine.join

.. autofunction:: cocotb.decorators.RunningCoroutine.kill

Triggers
--------
See :ref:`simulator-triggers` for a list of sub-classes. Below are the internal
classes used within ``cocotb``.

.. currentmodule:: cocotb.triggers

.. autoclass:: Trigger
    :members:
    :member-order: bysource

.. autoclass:: GPITrigger
    :members:
    :member-order: bysource

.. autoclass:: Waitable
    :members:
    :member-order: bysource
    :private-members:

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

.. autodata:: cocotb.plusargs

.. automodule:: cocotb.utils
    :members:
    :member-order: bysource
    :synopsis: Various utilities for testbench writers.

Simulation Object Handles
=========================

.. inheritance-diagram:: cocotb.handle
   :parts: 1

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

Miscellaneous
=============

Signal Tracer for WaveDrom
--------------------------

.. automodule:: cocotb.wavedrom
    :members:
    :member-order: bysource
    :synopsis: A signal tracer for WaveDrom.


Developer-focused
=================

The Scheduler
-------------

.. note::
    The scheduler object should generally not be interacted with directly -
    the only part of it that a user will need is encapsulated in :func:`~cocotb.fork`,
    everything else works behind the scenes.

.. currentmodule:: cocotb.scheduler

.. autodata:: cocotb.scheduler

.. autoclass:: Scheduler
    :members:
    :member-order: bysource


The ``cocotb-config`` script
----------------------------

.. argparse::
    :module: cocotb.config
    :func: get_parser
    :prog: cocotb-config
