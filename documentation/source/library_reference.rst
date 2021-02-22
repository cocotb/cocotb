*****************
Library Reference
*****************

.. spelling::
   AXIProtocolError
   BusDriver
   De
   Re
   ReadOnly
   args
   cbNextSimTime
   ing
   sim
   stdout
   un


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
    :exclude-members: get_value, get_buff, get_binstr, get_value_signed

.. autofunction:: cocotb.fork

.. autofunction:: cocotb.decorators.RunningTask.join

.. autofunction:: cocotb.decorators.RunningTask.kill

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

These are provided by the `cocotb-bus <https://github.com/cocotb/cocotb-bus>`_ package.

Bus
---

.. autoclass:: cocotb_bus.bus.Bus
    :members:
    :member-order: bysource

Driver
------

.. autoclass:: cocotb_bus.drivers.Driver
    :members:
    :member-order: bysource
    :private-members:

.. autoclass:: cocotb_bus.drivers.BitDriver
    :members:
    :member-order: bysource
    :show-inheritance:
    :private-members:

.. autoclass:: cocotb_bus.drivers.BusDriver
    :members:
    :member-order: bysource
    :show-inheritance:
    :private-members:

.. autoclass:: cocotb_bus.drivers.ValidatedBusDriver
    :members:
    :member-order: bysource
    :show-inheritance:
    :private-members:

Monitor
-------

.. autoclass:: cocotb_bus.monitors.Monitor
    :members:
    :member-order: bysource
    :private-members:

.. autoclass:: cocotb_bus.monitors.BusMonitor
    :members:
    :member-order: bysource
    :show-inheritance:
    :private-members:

Scoreboard
----------

.. automodule:: cocotb_bus.scoreboard
    :members:
    :member-order: bysource
    :show-inheritance:
    :synopsis: Class for scoreboards.

Generators
----------

.. automodule:: cocotb.generators
    :members:
    :member-order: bysource
    :show-inheritance:
    :synopsis: Class for generators.

Bit
^^^

.. automodule:: cocotb.generators.bit
    :members:
    :member-order: bysource
    :show-inheritance:


Byte
^^^^

.. automodule:: cocotb.generators.byte
    :members:
    :member-order: bysource
    :show-inheritance:

..
   Needs scapy

   Packet
   ^^^^^^

   .. automodule:: cocotb.generators.packet
       :members:
       :member-order: bysource
       :show-inheritance:

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

.. _logging-reference-section:

Logging
-------

.. currentmodule:: cocotb.log

.. autofunction:: default_config

.. autoclass:: SimLogFormatter
    :show-inheritance:
    :no-members:

.. autoclass:: SimColourLogFormatter
    :show-inheritance:
    :no-members:

.. autoclass:: SimTimeContextFilter
    :show-inheritance:
    :no-members:

.. currentmodule:: None

.. attribute:: logging.LogRecord.created_sim_time

    The result of :func:`get_sim_time` at the point the log was created
    (in simulator units). The formatter is responsible for converting this
    to something like nanoseconds via :func:`~cocotb.utils.get_time_from_sim_steps`.

    This is added by :class:`cocotb.log.SimTimeContextFilter`.


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
    :exclude-members: Deposit, Force, Freeze, Release
..
   Excluding the Assignment Methods that are getting their own section below

.. _assignment-methods:

Assignment Methods
------------------

.. currentmodule:: cocotb.handle

.. autoclass:: Deposit

.. autoclass:: Force

.. autoclass:: Freeze

.. autoclass:: Release


Implemented Testbench Structures
================================

Drivers
-------

AMBA
^^^^

Advanced Microcontroller Bus Architecture.

.. currentmodule:: cocotb_bus.drivers.amba

.. autoclass:: AXI4Master
    :members:
    :member-order: bysource

.. autoclass:: AXI4LiteMaster
    :members:
    :member-order: bysource

.. autoclass:: AXI4Slave
    :members:
    :member-order: bysource


Avalon
^^^^^^

.. currentmodule:: cocotb_bus.drivers.avalon

.. autoclass:: AvalonMM
    :members:
    :member-order: bysource
    :show-inheritance:

.. autoclass:: AvalonMaster
    :members:
    :member-order: bysource
    :show-inheritance:

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
^^^

.. currentmodule:: cocotb_bus.drivers.opb

.. autoclass:: OPBMaster
    :members:
    :member-order: bysource
    :show-inheritance:


XGMII
^^^^^

.. currentmodule:: cocotb_bus.drivers.xgmii

.. autoclass:: XGMII
    :members:
    :member-order: bysource
    :show-inheritance:

Monitors
--------

Avalon
^^^^^^

.. currentmodule:: cocotb_bus.monitors.avalon

.. autoclass:: AvalonST
    :members:
    :member-order: bysource
    :show-inheritance:

.. autoclass:: AvalonSTPkts
    :members:
    :member-order: bysource
    :show-inheritance:

XGMII
^^^^^

.. autoclass:: cocotb_bus.monitors.xgmii.XGMII
    :members:
    :member-order: bysource
    :show-inheritance:

Miscellaneous
=============

Asynchronous Queues
-------------------

.. automodule:: cocotb.queue
    :members:
    :member-order: bysource

Other Runtime Information
-------------------------

.. autodata:: cocotb.argv

.. autodata:: cocotb.SIM_NAME

.. autodata:: cocotb.SIM_VERSION

.. autodata:: cocotb.RANDOM_SEED

.. autodata:: cocotb.plusargs

.. autodata:: cocotb.LANGUAGE

.. autodata:: cocotb.top


Signal Tracer for WaveDrom
--------------------------

.. automodule:: cocotb.wavedrom
    :members:
    :member-order: bysource
    :synopsis: A signal tracer for WaveDrom.


Implementation Details
======================

.. note::
    In general, nothing in this section should be interacted with directly -
    these components work mostly behind the scenes.

The Scheduler
-------------

.. currentmodule:: cocotb.scheduler

.. autodata:: cocotb.scheduler

.. autoclass:: Scheduler
    :members:
    :member-order: bysource

The Regression Manager
----------------------

.. currentmodule:: cocotb.regression

.. autodata:: cocotb.regression_manager

.. autoclass:: RegressionManager
    :members:
    :member-order: bysource


The ``cocotb.simulator`` module
-------------------------------

This module is a Python wrapper to libgpi.
It should not be considered public API, but is documented here for developers
of cocotb.

.. automodule:: cocotb.simulator
    :members:
    :undoc-members:
    :member-order: bysource


The ``cocotb-config`` script
----------------------------

.. argparse::
    :module: cocotb.config
    :func: get_parser
    :prog: cocotb-config
