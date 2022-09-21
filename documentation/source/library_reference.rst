*****************
Library Reference
*****************

.. spelling:word-list::
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

.. autoclass:: cocotb.regression.TestFactory
    :members:
    :member-order: bysource

Interacting with the Simulator
==============================

.. _task-management:

Task Management
---------------

.. autofunction:: cocotb.fork

.. autofunction:: cocotb.start_soon

.. autofunction:: cocotb.start

.. autofunction:: cocotb.create_task

.. autoclass:: cocotb.decorators.Task
    :members:

Handle Values
-------------

.. currentmodule:: cocotb.binary

.. autoclass:: BinaryRepresentation
    :members:
    :member-order: bysource

.. autoclass:: BinaryValue
    :members:
    :member-order: bysource
    :exclude-members: get_value, get_buff, get_binstr, get_value_signed

HDL Datatypes
-------------

These are a set of datatypes that model the behavior of common HDL datatypes.
They can be used independently of cocotb for modeling and will replace :class:`BinaryValue`
as the types used by cocotb's `simulator handles <#simulation-object-handles>`_.

.. versionadded:: 1.6.0

.. autoclass:: cocotb.types.Logic

.. autoclass:: cocotb.types.Bit

.. autoclass:: cocotb.types.Range
    :members:
    :exclude-members: count, index

.. autofunction:: cocotb.types.concat

.. autoclass:: cocotb.types.Array
    :members:
    :exclude-members: count, index

.. autoclass:: cocotb.types.LogicArray
    :members:

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

    The result of :func:`~cocotb.utils.get_sim_time` at the point the log was created
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
    :special-members: __len__
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

Other Handle Methods
--------------------

.. currentmodule:: None

.. function:: len(handle)

   Return the "length" (the number of elements) of the underlying object.

   For vectors this is the number of bits.


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
