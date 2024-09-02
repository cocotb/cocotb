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

.. currentmodule:: cocotb_tools.runner

..
   .. module:: cocotb_tools.runner
       :synopsis: Build HDL and run cocotb tests.

.. autodoc2-object:: cocotb_tools.runner.get_runner

.. autodoc2-object:: cocotb_tools.runner.Runner
..
    :members:

.. autodoc2-object:: cocotb_tools.runner.VHDL

.. autodoc2-object:: cocotb_tools.runner.Verilog

.. autodata:: MAX_PARALLEL_BUILD_JOBS

Simulator Runners
-----------------

.. autodoc2-object:: cocotb_tools.runner.Icarus

.. autodoc2-object:: cocotb_tools.runner.Verilator

.. autodoc2-object:: cocotb_tools.runner.Riviera

.. autodoc2-object:: cocotb_tools.runner.Questa

.. autodoc2-object:: cocotb_tools.runner.Xcelium

.. autodoc2-object:: cocotb_tools.runner.Ghdl

.. autodoc2-object:: cocotb_tools.runner.Nvc

Results
-------

.. autodoc2-object:: cocotb_tools.runner.get_results

File Utilities
--------------

.. autodoc2-object:: cocotb_tools.runner.get_abs_path

.. autodoc2-object:: cocotb_tools.runner.get_abs_paths

.. autodoc2-object:: cocotb_tools.runner.outdated

.. autodoc2-object:: cocotb_tools.runner.UnknownFileExtension


.. _writing-tests:

Writing and Generating Tests
============================

.. autodoc2-object:: cocotb.test

.. autofunction:: cocotb.parametrize

.. autodoc2-object:: cocotb.regression.TestFactory
..
    :members:
    :member-order: bysource

.. autoclass:: cocotb.result.TestSuccess

Interacting with the Simulator
==============================

.. _task-management:

Task Management
---------------

.. autodoc2-object:: cocotb.start_soon

.. autodoc2-object:: cocotb.start

.. autodoc2-object:: cocotb.create_task

.. autodoc2-object:: cocotb.task.ResultType

.. autodoc2-object:: cocotb.task.Task
..
    :members:

Dealing with non-``async`` code
-------------------------------

.. autodoc2-object:: cocotb.bridge

.. autodoc2-object:: cocotb.resume

HDL Datatypes
-------------

These are a set of datatypes that model the behavior of common HDL datatypes.

.. versionadded:: 1.6

.. autodoc2-object:: cocotb.types.Logic

.. autodoc2-object:: cocotb.types.Range
..
    :members:
    :exclude-members: count, index

.. autodoc2-object:: cocotb.types.Array
..
    :members:
    :inherited-members:

.. autodoc2-object:: cocotb.types.LogicArray
..
    :members:
    :inherited-members:

.. autoclass:: cocotb.types.logic_array.ResolveX

.. autodata:: cocotb.types.logic_array.RESOLVE_X


Triggers
========

.. _simulator-triggers:

Simulator Triggers
------------------

.. _edge-triggers:

Edge Triggers
^^^^^^^^^^^^^

.. autoclass:: cocotb.triggers.ValueChange

.. autoclass:: cocotb.triggers.Edge

.. autoclass:: cocotb.triggers.RisingEdge

.. autoclass:: cocotb.triggers.FallingEdge

.. autodoc2-object:: cocotb.triggers.ClockCycles


Timing
^^^^^^

.. autodoc2-object:: cocotb.triggers.Timer

.. autodoc2-object:: cocotb.triggers.ReadOnly

.. autodoc2-object:: cocotb.triggers.ReadWrite

.. autodoc2-object:: cocotb.triggers.NextTimeStep


.. _python-triggers:

Python Triggers
---------------

.. autodoc2-object:: cocotb.triggers.NullTrigger

.. autodoc2-object:: cocotb.triggers.Combine

.. autodoc2-object:: cocotb.triggers.First

.. autofunction:: cocotb.triggers.Join

.. autoclass:: cocotb.triggers.TaskComplete
    :members:


Synchronization
^^^^^^^^^^^^^^^

The following objects are not :class:`Trigger`\ s themselves, but contain methods that can be used as triggers.
They are used to synchronize coroutines with each other.

.. autodoc2-object:: cocotb.triggers.Event
..
    :members:
    :member-order: bysource

.. autodoc2-object:: cocotb.triggers.Lock
..
    :members:
    :member-order: bysource

.. autoclass:: cocotb.triggers.SimTimeoutError

.. autofunction:: cocotb.triggers.with_timeout


Triggers (Internals)
--------------------

The following are internal classes used within ``cocotb``.

.. currentmodule:: cocotb.triggers

.. autodoc2-object:: cocotb.triggers.Trigger
..
    :members:
    :member-order: bysource

.. autodoc2-object:: cocotb.triggers.GPITrigger
..
    :members:
    :member-order: bysource

.. autodoc2-object:: cocotb.triggers.Waitable
..
    :members:
    :member-order: bysource
    :private-members:


Test Utilities
==============

Clock Driver
------------

.. autodoc2-object:: cocotb.clock.Clock
..
    :members:
    :member-order: bysource

Asynchronous Queues
-------------------

.. autodoc2-object:: cocotb.queue
..
    :members:
    :member-order: bysource
    :synopsis: Asynchronous queues.


Simulation Time Utilities
=========================

.. autodoc2-object:: cocotb.utils
..
    :members:
    :member-order: bysource
    :synopsis: Various utilities for dealing with simulation time.


.. _logging-reference-section:

Logging
=======

.. module:: cocotb.logging
    :synopsis: Classes for logging messages from cocotb during simulation.

.. autodoc2-object:: cocotb.log

.. autodoc2-object:: cocotb.logging.default_config

.. autodoc2-object:: cocotb.logging.SimLogFormatter
..
    :show-inheritance:
    :no-members:

.. autodoc2-object:: cocotb.logging.SimColourLogFormatter
..
    :show-inheritance:
    :no-members:

.. autodoc2-object:: cocotb.logging.SimTimeContextFilter
..
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

.. autodoc2-object:: cocotb.handle
..
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

.. autodoc2-object:: cocotb.handle.Deposit

.. autodoc2-object:: cocotb.handle.Force

.. autodoc2-object:: cocotb.handle.Freeze

.. autodoc2-object:: cocotb.handle.Release


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

Other Runtime Information
-------------------------

.. autodoc2-object:: cocotb.argv

.. autodoc2-object:: cocotb.SIM_NAME

.. autodoc2-object:: cocotb.SIM_VERSION

.. autodoc2-object:: cocotb.plusargs

.. autodoc2-object:: cocotb.packages

.. autodoc2-object:: cocotb.top

.. autodoc2-object:: cocotb.is_simulation

.. autodoc2-object:: cocotb.sim_phase

.. autodoc2-object:: cocotb.SimPhase

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

.. autodoc2-object:: cocotb.regression_manager

.. autodoc2-object:: cocotb.regression.Test

.. autodoc2-object:: cocotb.regression.RegressionMode

.. autodoc2-object:: cocotb.regression.RegressionManager
..
    :members:
    :member-order: bysource

The ``cocotb.simulator`` module (Internals)
-------------------------------------------

This module is a Python wrapper to libgpi.
It should not be considered public API, but is documented here for developers
of cocotb.

.. automodule:: cocotb.simulator
    :members:
    :undoc-members:
    :member-order: bysource
    :synopsis: Interface to simulator.
