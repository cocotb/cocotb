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

.. _api-runner:

Python Test Runner
==================

.. warning::
    Python runners and associated APIs are an experimental feature and subject to change.

.. automodule:: cocotb_tools.runner
    :members:
    :member-order: bysource
    :synopsis: Build HDL and run cocotb tests.


Test Results
============

The exceptions in this module can be raised at any point by any code and will terminate the test.

.. automodule:: cocotb.result
    :members:
    :member-order: bysource
    :synopsis: Exceptions and functions for simulation result handling.


.. _writing-tests:

Writing and Generating tests
============================

.. autofunction:: cocotb.test

.. autofunction:: cocotb.external

.. autofunction:: cocotb.function

.. autofunction:: cocotb.parameterize

.. autoclass:: cocotb.regression.TestFactory
    :members:
    :member-order: bysource

Interacting with the Simulator
==============================

.. _task-management:

Task Management
---------------

.. autofunction:: cocotb.start_soon

.. autofunction:: cocotb.start

.. autofunction:: cocotb.create_task

.. autoclass:: cocotb.task.Task
    :members:

HDL Datatypes
-------------

These are a set of datatypes that model the behavior of common HDL datatypes.

.. versionadded:: 1.6.0

.. autoclass:: cocotb.types.Logic

.. autoclass:: cocotb.types.Range
    :members:
    :exclude-members: count, index

.. autoclass:: cocotb.types.Array
    :members:
    :inherited-members:

.. autoclass:: cocotb.types.LogicArray
    :members:
    :inherited-members:


Triggers
========

.. _simulator-triggers:

Simulator Triggers
------------------

Signals
^^^^^^^

.. autoclass:: cocotb.triggers.Edge(signal)

.. autoclass:: cocotb.triggers.RisingEdge(signal)

.. autoclass:: cocotb.triggers.FallingEdge(signal)

.. autoclass:: cocotb.triggers.ClockCycles


Timing
^^^^^^

.. autoclass:: cocotb.triggers.Timer

.. autoclass:: cocotb.triggers.ReadOnly()

.. autoclass:: cocotb.triggers.ReadWrite()

.. autoclass:: cocotb.triggers.NextTimeStep()


.. _python-triggers:

Python Triggers
---------------

.. autoclass:: cocotb.triggers.Combine

.. autoclass:: cocotb.triggers.First

.. autoclass:: cocotb.triggers.Join(coroutine)
    :members: retval


Synchronization
^^^^^^^^^^^^^^^

These are not :class:`Trigger`\ s themselves, but contain methods that can be used as triggers.
These are used to synchronize coroutines with each other.

.. autoclass:: cocotb.triggers.Event
    :members:
    :member-order: bysource

.. autoclass:: cocotb.triggers.Lock
    :members:
    :member-order: bysource

.. autofunction:: cocotb.triggers.with_timeout


Triggers (Internals)
--------------------

The following are internal classes used within ``cocotb``.

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

.. module:: cocotb.logging
    :synopsis: Classes for logging messages from cocotb during simulation.

.. autodata:: cocotb.log

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

.. image:: diagrams/svg/inheritance-cocotb.handle.svg
   :alt: The class inheritance diagram for cocotb.handle

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

.. function:: dir(handle)

   Return a list of the sub-handles of *handle*,
   that is, the instances, signals, constants etc. of a certain hierarchy level in the DUT.

Miscellaneous
=============

Asynchronous Queues
-------------------

.. automodule:: cocotb.queue
    :members:
    :member-order: bysource
    :synopsis: Asynchronous queues.

Other Runtime Information
-------------------------

.. autodata:: cocotb.argv

.. autodata:: cocotb.SIM_NAME

.. autodata:: cocotb.SIM_VERSION

.. autodata:: cocotb.plusargs

.. autodata:: cocotb.packages

.. autodata:: cocotb.top

.. autodata:: cocotb.is_simulation

.. _combine-results:

The ``combine_results`` script
------------------------------

Use ``python -m cocotb_tools.combine_results`` to call the script.

.. sphinx_argparse_cli::
    :module: cocotb_tools.combine_results
    :func: _get_parser
    :prog: combine_results

.. _cocotb-config:

The ``cocotb-config`` script
----------------------------

Use ``cocotb-config`` or ``python -m cocotb_tools.config`` to call the script.

.. sphinx_argparse_cli::
    :module: cocotb_tools.config
    :func: _get_parser
    :prog: cocotb-config


Implementation Details
======================

.. note::
    In general, nothing in this section should be interacted with directly -
    these components work mostly behind the scenes.

The Regression Manager
----------------------

.. module:: cocotb.regression
    :synopsis: Regression test suite manager.

.. autodata:: cocotb.regression_manager

.. autoclass:: Test

.. autoenum:: RegressionMode

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
    :synopsis: Interface to simulator.
