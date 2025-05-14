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

.. module:: cocotb_tools.runner
    :synopsis: Build HDL and run cocotb tests.

.. autofunction:: get_runner

.. autoclass:: Runner
    :members:

.. autoclass:: VHDL

.. autoclass:: Verilog

.. autodata:: MAX_PARALLEL_BUILD_JOBS

Simulator Runners
-----------------

.. autoclass:: Icarus

.. autoclass:: Verilator

.. autoclass:: Riviera

.. autoclass:: Questa

.. autoclass:: Xcelium

.. autoclass:: Ghdl

.. autoclass:: Nvc

.. autoclass:: Vcs

.. autoclass:: Dsim

Results
-------

.. autofunction:: get_results

File Utilities
--------------

.. autofunction:: get_abs_path

.. autofunction:: get_abs_paths

.. autofunction:: outdated

.. autoclass:: UnknownFileExtension


.. _writing-tests:

Writing and Generating Tests
============================

.. autofunction:: cocotb.test

.. autofunction:: cocotb.parametrize

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

.. autoclass:: cocotb.task.ResultType

.. autoclass:: cocotb.task.Task
    :members:

Dealing with non-``async`` code
-------------------------------

.. autofunction:: cocotb.task.bridge

.. autofunction:: cocotb.task.resume

HDL Datatypes
-------------

These are a set of datatypes that model the behavior of common HDL datatypes.

.. versionadded:: 1.6

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

.. _triggers::

Triggers
========

.. autofunction:: cocotb.triggers.current_gpi_trigger

.. _edge-triggers:

Edge Triggers
-------------

.. autoclass:: cocotb.triggers.RisingEdge
    :members:

.. autoclass:: cocotb.triggers.FallingEdge
    :members:

.. autoclass:: cocotb.triggers.ClockCycles
    :members:

.. autoclass:: cocotb.triggers.ValueChange
    :members:

.. autoclass:: cocotb.triggers.Edge
    :members:


Timing Triggers
---------------

.. autoclass:: cocotb.triggers.Timer
    :members:

.. autoclass:: cocotb.triggers.ReadOnly
    :members:

.. autoclass:: cocotb.triggers.ReadWrite
    :members:

.. autoclass:: cocotb.triggers.NextTimeStep
    :members:


Concurrency Triggers
--------------------

Triggers dealing with Tasks or running multiple Tasks concurrently.

.. autoclass:: cocotb.task.Join
    :members:

.. autoclass:: cocotb.task.TaskComplete
    :members:

.. autoclass:: cocotb.triggers.NullTrigger
    :members:

.. autoclass:: cocotb.triggers.Combine
    :members:

.. autoclass:: cocotb.triggers.First
    :members:


Synchronization Triggers
------------------------

The following objects are not :class:`Trigger`\ s themselves, but contain methods that can be used as triggers.
They are used to synchronize coroutines with each other.

.. autoclass:: cocotb.triggers.Event
    :members:
    :member-order: bysource

.. autoclass:: cocotb.triggers.Lock
    :members:
    :member-order: bysource

.. autoclass:: cocotb.triggers.SimTimeoutError

.. autofunction:: cocotb.triggers.with_timeout


Abstract Triggers
-----------------

The following are internal classes used within ``cocotb``.

.. autoclass:: cocotb.triggers.Trigger
    :members:
    :member-order: bysource

.. autoclass:: cocotb.triggers.GPITrigger
    :members:
    :member-order: bysource

.. autoclass:: cocotb.triggers.Waitable
    :members:
    :member-order: bysource
    :private-members:


Test Utilities
==============

Clock Driver
------------

.. autoclass:: cocotb.clock.Clock
    :members:
    :member-order: bysource

Asynchronous Queues
-------------------

.. automodule:: cocotb.queue
    :members:
    :member-order: bysource
    :synopsis: Asynchronous queues.


Simulation Time Utilities
=========================

.. automodule:: cocotb.utils
    :members:
    :member-order: bysource
    :synopsis: Various utilities for dealing with simulation time.


.. _logging-reference-section:

Logging
=======

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

    The result of :func:`~cocotb.utils.get_sim_time` at the point the log was created (in simulation time).
    The formatter is responsible for converting this to something like nanoseconds via :func:`~cocotb.utils.get_time_from_sim_steps`.

    This is added by :class:`cocotb.log.SimTimeContextFilter`.


Simulator Objects
=================

.. note::
    "Handle" is a legacy term which refers to the fact these objects are implemented using opaque "handles" to simulator objects.
    A better term is :term:`simulator object`.

.. module:: cocotb.handle

.. autoclass:: SimHandleBase
    :members:
    :member-order: bysource

.. autoenum:: GPIDiscovery

.. autoclass:: HierarchyObject
    :members:
    :member-order: bysource
    :special-members: __len__, __iter__
    :inherited-members: SimHandleBase

.. autoclass:: HierarchyArrayObject
    :members:
    :member-order: bysource
    :special-members: __len__, __iter__
    :inherited-members: SimHandleBase

.. autoclass:: ValueObjectBase
    :members:
    :member-order: bysource
    :inherited-members: SimHandleBase

.. autoclass:: ArrayObject
    :members:
    :member-order: bysource
    :special-members: __len__, __iter__
    :inherited-members: SimHandleBase, ValueObjectBase

.. autoclass:: LogicObject
    :members:
    :member-order: bysource
    :inherited-members: SimHandleBase, ValueObjectBase

.. autoclass:: LogicArrayObject
    :members:
    :member-order: bysource
    :special-members: __len__
    :inherited-members: SimHandleBase, ValueObjectBase

.. autoclass:: StringObject
    :members:
    :member-order: bysource
    :special-members: __len__
    :inherited-members: SimHandleBase, ValueObjectBase

.. autoclass:: IntegerObject
    :members:
    :member-order: bysource
    :inherited-members: SimHandleBase, ValueObjectBase

.. autoclass:: RealObject
    :members:
    :member-order: bysource
    :inherited-members: SimHandleBase, ValueObjectBase

.. autoclass:: EnumObject
    :members:
    :member-order: bysource
    :inherited-members: SimHandleBase, ValueObjectBase

.. _assignment-methods:

Assignment Methods
------------------

.. autoclass:: Deposit

.. autoclass:: Immediate

.. autoclass:: Force

.. autoclass:: Freeze

.. autoclass:: Release

.. module:: None

Miscellaneous
=============

Test Control
------------

.. autofunction:: cocotb.pass_test

Other Runtime Information
-------------------------

.. autodata:: cocotb.argv

.. autodata:: cocotb.plusargs

.. autodata:: cocotb.top

.. autodata:: cocotb.packages

.. autodata:: cocotb.SIM_NAME

.. autodata:: cocotb.SIM_VERSION

.. autodata:: cocotb.RANDOM_SEED

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

.. autodata:: cocotb._regression_manager

.. autoclass:: Test

.. autoenum:: RegressionMode

.. autoclass:: RegressionManager
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
