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

.. module:: cocotb

.. _api-runner:

Python Test Runner
==================

.. warning::
    Python runners and associated APIs are an experimental feature and subject to change.

.. module:: cocotb_tools.runner
    :synopsis: Build HDL and run cocotb tests.

.. autofunction:: get_runner

.. autoclass:: Runner
    :members:

.. autoclass:: VHDL

.. autoclass:: Verilog

.. autoclass:: VerilatorControlFile

.. autodata:: MAX_PARALLEL_BUILD_JOBS

.. envvar:: GUI

    Set this to 1 to enable the GUI mode in the simulator (if supported).

.. envvar:: WAVES

    Set this to 1 to enable wave traces dump for the
    Aldec Riviera-PRO, Mentor Graphics Questa, and Icarus Verilog simulators.
    To get wave traces in Verilator see :ref:`sim-verilator-waveforms`.

.. envvar:: COCOTB_WAVEFORM_VIEWER

    The name of the waveform viewer executable to use (like ``surfer``) when GUI mode is enabled
    for simulators that do not have a built-in waveform viewer (like Verilator).
    The executable name will be called with the name of the waveform file as the argument.


.. _api-runner-sim:

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

Marking and Generating Tests
============================

.. currentmodule:: None

.. autofunction:: cocotb.test

.. autofunction:: cocotb.parametrize

.. autoclass:: cocotb.regression.TestFactory
    :members:
    :member-order: bysource

.. autoclass:: cocotb.regression.SimFailure


Discovering Tests
=================

.. envvar:: COCOTB_TEST_MODULES

    The name of the Python module(s) to search for test functions -
    if your tests are in a file called ``test_mydesign.py``, ``COCOTB_TEST_MODULES`` would be set to ``test_mydesign``.
    Multiple modules can be specified using a comma-separated string.
    For example: ``COCOTB_TEST_MODULES="directed_tests,random_tests,error_injection_tests"``.
    All tests will be run from each specified module in order of the module's appearance in this list.

    This is the only environment variable that is **required** for cocotb, all others are optional.

    .. versionchanged:: 2.0

        :envvar:`MODULE` is renamed to :envvar:`COCOTB_TEST_MODULES`.

    .. deprecated:: 2.0

        :envvar:`MODULE` is a deprecated alias and will be removed.

.. _testcase:

.. envvar:: COCOTB_TESTCASE

    A comma-separated list of tests to run.
    Does an exact match on the test name.

    .. versionchanged:: 2.0

        :envvar:`TESTCASE` is renamed to :envvar:`COCOTB_TESTCASE`.

    .. deprecated:: 2.0

        :envvar:`TESTCASE` is a deprecated alias and will be removed.

    .. deprecated:: 2.0

        Use :envvar:`COCOTB_TEST_FILTER` instead.

        If matching only the exact test name is desired, use the regular expression anchor character ``$``.
        For example, ``my_test$`` will match ``my_test``, but not ``my_test_2``.

        To run multiple tests, use regular expression alternations.
        For example, ``my_test|my_other_test``.

    .. versionchanged:: 2.0

        Previously, if more than one test matched a test name in the :envvar:`TESTCASE` list,
        only the first test that matched that test name in the :envvar:`COCOTB_TEST_MODULES` list was run.
        Now, all tests that match the test name across all :envvar:`COCOTB_TEST_MODULES`\ s are run.

    .. warning::

        Only one of :envvar:`COCOTB_TESTCASE` or :envvar:`COCOTB_TEST_FILTER` should be used.


.. envvar:: COCOTB_TEST_FILTER

    A regular expression matching names of test function(s) to run.
    If this variable is not defined cocotb discovers and executes all functions decorated with the :class:`cocotb.test` decorator in the supplied :envvar:`COCOTB_TEST_MODULES` list.

    .. versionadded:: 2.0

    .. warning::

        Only one of :envvar:`COCOTB_TESTCASE` or :envvar:`COCOTB_TEST_FILTER` should be used.

.. envvar:: COCOTB_RESULTS_FILE

    The file name where xUnit XML tests results are stored. If not provided, the default is :file:`results.xml`.

    .. versionadded:: 1.3

.. envvar:: COCOTB_REWRITE_ASSERTION_FILES

    Select the Python files to apply ``pytest``'s assertion rewriting to.
    This is useful to get more informative assertion error messages in cocotb tests.
    Specify using a space-separated list of file globs, e.g. ``test_*.py testbench_common/**/*.py``.
    Set to the empty string to disable assertion rewriting.
    Defaults to ``*.py`` (all Python files, even third-party modules like ``scipy``).

    .. versionadded:: 2.0

Test Management
===============

.. currentmodule:: None

.. autofunction:: cocotb.pass_test

.. _task-management:

Task Management
===============

.. currentmodule:: None

.. autofunction:: cocotb.start_soon

.. autofunction:: cocotb.start

.. autofunction:: cocotb.create_task

.. module:: cocotb.task
    :synopsis: Tools for concurrency.

.. autoclass:: ResultType

.. autoclass:: Task
    :members:

.. autofunction:: current_task

Bridging through non-`async` code
---------------------------------

.. autofunction:: bridge

.. autofunction:: resume


HDL Datatypes
=============

These are a set of datatypes that model the behavior of common HDL datatypes.

.. versionadded:: 1.6

.. module:: cocotb.types
    :synopsis: Types for dealing with digital signal values.

.. autoclass:: Logic
    :members:

.. autoclass:: Bit
    :members:

.. autoclass:: Range
    :members:
    :exclude-members: count, index

.. autoclass:: AbstractArray
    :members:

.. autoclass:: AbstractMutableArray
    :members:
    :show-inheritance:

.. autoclass:: Array
    :members:
    :inherited-members:

.. autoclass:: LogicArray
    :members:
    :inherited-members:

.. envvar:: COCOTB_RESOLVE_X

    Defines how to resolve bits with a value of ``X``, ``Z``, ``U``, ``W``, or ``-`` when being converted to integer.
    Valid settings are:

    ``error``
        Resolves nothing.
    ``weak``
        Resolves ``L`` to ``0`` and ``H`` to ``1``.
    ``zeros``
        Like ``weak``, but resolves all other non-\ ``0``\ /\ ``1`` values to ``0``.
    ``ones``
        Like ``weak``, but resolves all other non-\ ``0``\ /\ ``1`` values to ``1``.
    ``random``
        Like ``weak``, but resolves all other non-\ ``0``\ /\ ``1`` values randomly to either ``0`` or ``1``.

    There is also a slight difference in behavior of ``bool(logic)`` when this environment variable is set.
    When this variable is set, ``bool(logic)`` treats all non-\ ``0``\ /\ ``1`` values as equivalent to ``0``.
    When this variable is *not* set, ``bool(logic)`` will fail on non-\ ``0``\ /\ ``1`` values.

    .. warning::
        Using this feature is *not* recommended.

    .. deprecated:: 2.0
        The previously accepted values ``VALUE_ERROR``, ``ZEROS``, ``ONES``, and ``RANDOM`` are deprecated.

.. _triggers:

Triggers
========

.. module:: cocotb.triggers

.. autofunction:: current_gpi_trigger

.. _edge-triggers:

Edge Triggers
-------------

.. autoclass:: RisingEdge
    :members:

.. autoclass:: FallingEdge
    :members:

.. autoclass:: ClockCycles
    :members:

.. autoclass:: ValueChange
    :members:

.. autoclass:: Edge
    :members:


Timing Triggers
---------------

.. autoclass:: Timer
    :members:

    .. autoattribute:: round_mode

.. autoclass:: ReadOnly
    :members:

.. autoclass:: ReadWrite
    :members:

.. autoclass:: NextTimeStep
    :members:


Concurrency Triggers
--------------------

Triggers dealing with Tasks or running multiple Tasks concurrently.

.. currentmodule:: None

.. autoclass:: cocotb.task.Join
    :members:

.. autoclass:: cocotb.task.TaskComplete
    :members:

.. currentmodule:: cocotb.triggers

.. autoclass:: NullTrigger
    :members:

.. autoclass:: Combine
    :members:

.. autoclass:: First
    :members:


Synchronization Triggers
------------------------

The following objects are not :class:`Trigger`\ s themselves, but contain methods that can be used as triggers.
They are used to synchronize coroutines with each other.

.. autoclass:: Event
    :members:
    :member-order: bysource

.. autoclass:: Lock
    :members:
    :member-order: bysource

.. autoclass:: SimTimeoutError

.. autofunction:: with_timeout


Abstract Triggers
-----------------

The following are internal classes used within ``cocotb``.

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


Test Utilities
==============

Clock Driver
------------

.. automodule:: cocotb.clock
    :members:
    :member-order: bysource
    :synopsis: A single-ended clock driver.

Asynchronous Queues
-------------------

.. automodule:: cocotb.queue
    :members:
    :inherited-members:
    :member-order: bysource
    :synopsis: Collection of asynchronous queues.


Simulation Time Utilities
=========================

.. automodule:: cocotb.simtime
    :members:
    :member-order: bysource
    :synopsis: Tools for dealing with simulated time.

.. automodule:: cocotb.utils
    :members:
    :member-order: bysource
    :synopsis: Tools for dealing with simulated time.
    :ignore-module-all:

.. _logging-reference-section:

Logging
=======

.. autodata:: cocotb.log

.. module:: cocotb.logging
    :synopsis: Classes for logging messages from cocotb during simulation.

.. autofunction:: SimLog

.. autofunction:: default_config

.. envvar:: COCOTB_LOG_LEVEL

    The default log level of all ``"cocotb"`` Python loggers.
    Valid values are ``TRACE``, ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
    The default is unset, which means that the log level is inherited from the root logger.
    This behaves similarly to ``INFO``.

    .. versionchanged:: 2.0
        The root ``"gpi"`` logger level is no longer set when this environment variable is used.
        Use :envvar:`GPI_LOG_LEVEL` instead.

.. envvar:: GPI_LOG_LEVEL

    The default log level of all ``"gpi"`` (the low-level simulator interface) loggers,
    including both Python and the native GPI logger.
    Valid values are ``TRACE``, ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
    The default is unset, which means that the log level is inherited from the root logger.
    This behaves similarly to ``INFO``.

    .. versionadded:: 2.0

Adding Simulation Time to Logs
------------------------------

.. autoclass:: SimTimeContextFilter
    :show-inheritance:
    :no-members:

.. currentmodule:: None

.. attribute:: logging.LogRecord.created_sim_time

    The result of :func:`~cocotb.simtime.get_sim_time` at the point the log was created (in simulation time).
    The formatter is responsible for converting this to something like nanoseconds via :func:`~cocotb.simtime.convert`.

    This is added by :class:`~cocotb.logging.SimTimeContextFilter`.

.. currentmodule:: cocotb.logging

Log Formatting
--------------

.. autoclass:: SimLogFormatter
    :show-inheritance:
    :no-members:

.. autoclass:: SimColourLogFormatter
    :show-inheritance:
    :no-members:

.. envvar:: COCOTB_REDUCED_LOG_FMT

    Defaults to ``1``.
    Logs will include simulation time, message type (``INFO``, ``WARNING``, ``ERROR``, ...), logger name, and the log message itself.
    If the value is set to ``0``, the filename and line number where a log function was called will be added between the logger name and the log message.

.. envvar:: COCOTB_LOG_PREFIX

    Customize the log message prefix.
    The value of this variable should be in Python f-string syntax.
    It has access to the following variables:

    - ``record``: The :class:`~logging.LogRecord` being formatted. This includes the attribute ``created_sim_time``, which is the simulation time in steps.
    - ``time``: The Python :mod:`time` module.
    - ``simtime``: The cocotb :mod:`cocotb.simtime` module.
    - ``ANSI``: The cocotb :class:`cocotb.logging.ANSI` enum, which contains ANSI escape codes for coloring the output.

    The following example is a color-less version of the default log prefix.

    .. code-block:: shell

        COCOTB_LOG_PREFIX="{simtime.convert(record.created_sim_time, 'step', to='ns'):>9}ns {record.levelname:<8} {record.name[-34:]:<34} "

    .. note::
        If this variable is set, :envvar:`COCOTB_REDUCED_LOG_FMT` has no effect.

Log Coloring
------------

.. autodata:: strip_ansi

.. autodata:: ANSI

.. envvar:: COCOTB_ANSI_OUTPUT

    Use this to override the default behavior of annotating cocotb output with
    ANSI color codes if the output is a terminal (``isatty()``).

    ``COCOTB_ANSI_OUTPUT=1``
       Forces output to be ANSI-colored regardless of the type of ``stdout`` or the presence of :envvar:`NO_COLOR`.
    ``COCOTB_ANSI_OUTPUT=0``
       Suppresses the ANSI color output in the log messages.

.. envvar:: NO_COLOR

    From http://no-color.org,

        All command-line software which outputs text with ANSI color added should check for the presence
        of a ``NO_COLOR`` environment variable that, when present (regardless of its value), prevents the addition of ANSI color.


Simulator Objects
=================

.. note::
    "Handle" is a legacy term which refers to the fact these objects are implemented using opaque "handles" to simulator objects.
    A better term is :term:`simulator object`.

.. module:: cocotb.handle
    :synopsis: Tools for discovering and manipulating :term:`simulator objects <simulator object>`.

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

.. envvar:: COCOTB_TRUST_INERTIAL_WRITES

    Defining this variable enables a mode which allows cocotb to trust that VPI/VHPI/FLI inertial writes are applied properly according to the respective standards.
    This mode can lead to noticeable performance improvements,
    and also includes some behavioral difference that are considered by the cocotb maintainers to be "better".
    Not all simulators handle inertial writes properly, so use with caution.

    This is achieved by *not* scheduling writes to occur at the beginning of the ``ReadWrite`` mode,
    but instead trusting that the simulator's inertial write mechanism is correct.
    This allows cocotb to avoid a VPI callback into Python to apply writes.

    .. note::
        This flag is enabled by default for the GHDL, NVC and Verilator simulators.
        More simulators may enable this flag by default in the future as they are gradually updated to properly apply inertial writes according to the respective standard.

    .. note::
        To test if your simulator behaves correctly with your simulator and version,
        first clone the cocotb github repo and run:

        .. code-block::

            cd tests/test_cases/test_inertial_writes
            make simulator_test SIM=<your simulator here> TOPLEVEL_LANG=<vhdl or verilog>

        If the tests pass, your simulator and version apply inertial writes as expected and you can turn on :envvar:`COCOTB_TRUST_INERTIAL_WRITES`.

.. _assignment-methods:

Assignment Methods
------------------

.. autoclass:: Deposit

.. autoclass:: Immediate

.. autoclass:: Force

.. autoclass:: Freeze

.. autoclass:: Release

Miscellaneous
=============

Other Runtime Information
-------------------------

.. currentmodule:: None

.. autodata:: cocotb.__version__

.. autodata:: cocotb.argv

.. autodata:: cocotb.plusargs

.. envvar:: COCOTB_PLUSARGS

      "Plusargs" are options that are starting with a plus (``+``) sign.
      They are passed to the simulator and are also available within cocotb as :data:`cocotb.plusargs`.
      In the simulator, they can be read by the Verilog/SystemVerilog system functions
      ``$test$plusargs`` and ``$value$plusargs``.

    .. versionchanged:: 2.0

        :envvar:`PLUSARGS` is renamed to :envvar:`COCOTB_PLUSARGS`.

    .. deprecated:: 2.0

        :envvar:`PLUSARGS` is a deprecated alias and will be removed.

.. autodata:: cocotb.top

.. envvar:: COCOTB_TOPLEVEL

    Use this to indicate the instance in the hierarchy to use as the :term:`DUT`.
    If this isn't defined then the first root instance is used.
    Leading and trailing whitespace are automatically discarded.

    The DUT is available in cocotb tests as a Python object at :data:`cocotb.top`;
    and is also passed to all cocotb tests as the :ref:`first and only parameter <quickstart_creating_a_test>`.

    .. versionchanged:: 1.6 Strip leading and trailing whitespace

    .. versionchanged:: 2.0

        :envvar:`TOPLEVEL` is renamed to :envvar:`COCOTB_TOPLEVEL`.

    .. deprecated:: 2.0

        :envvar:`TOPLEVEL` is a deprecated alias and will be removed.

.. autodata:: cocotb.packages

.. autodata:: cocotb.SIM_NAME

.. autodata:: cocotb.SIM_VERSION

.. autodata:: cocotb.RANDOM_SEED

.. envvar:: COCOTB_RANDOM_SEED

    Seed the Python random module to recreate a previous test stimulus.
    At the beginning of every test a message is displayed with the seed used for that execution:

    .. code-block:: bash

             0.00ns INFO     cocotb                             Seeding Python random module with 1756566114


    To recreate the same stimuli use the following:

    .. code-block:: bash

       make COCOTB_RANDOM_SEED=1377424946

    The special :data:`cocotb.plusargs` ``+ntb_random_seed`` and ``+seed``, if present,
    are evaluated to set the random seed value if :envvar:`!COCOTB_RANDOM_SEED` is not set.
    ``+ntb_random_seed`` takes precedence over ``+seed``.

    .. versionchanged:: 2.0

        :envvar:`RANDOM_SEED` is renamed to :envvar:`COCOTB_RANDOM_SEED`.

    .. deprecated:: 2.0

        :envvar:`RANDOM_SEED` is a deprecated alias and will be removed.

    .. deprecated:: 2.0

        The setting of :envvar:`!COCOTB_RANDOM_SEED` using ``+ntb_random_seed`` and ``+seed`` :data:`!cocotb.plusargs`.


.. autodata:: cocotb.is_simulation

Debugging
---------

.. automodule:: cocotb.debug
    :members:
    :member-order: bysource
    :synopsis: Features for debugging cocotb's concurrency system.

.. envvar:: COCOTB_SCHEDULER_DEBUG

    Enable additional log output of the coroutine scheduler.

    This will default the value of :data:`~cocotb.debug.debug`,
    which can later be modified.

.. envvar:: COCOTB_PDB_ON_EXCEPTION

   If defined, cocotb will drop into the Python debugger (:mod:`pdb`) if a test fails with an exception.
   See also the :ref:`troubleshooting-attaching-debugger-python` subsection of :ref:`troubleshooting-attaching-debugger`.

.. envvar:: COCOTB_ATTACH

    In order to give yourself time to attach a debugger to the simulator process before it starts to run,
    you can set the environment variable :envvar:`COCOTB_ATTACH` to a pause time value in seconds.
    If set, cocotb will print the process ID (PID) to attach to and wait the specified time before
    actually letting the simulator run.

.. envvar:: COCOTB_ENABLE_PROFILING

    Enable performance analysis of the Python portion of cocotb. When set, a file :file:`test_profile.pstat`
    will be written which contains statistics about the cumulative time spent in the functions.

    From this, a callgraph diagram can be generated with `gprof2dot <https://github.com/jrfonseca/gprof2dot>`_ and ``graphviz``.

.. envvar:: COCOTB_USER_COVERAGE

    Enable to collect Python coverage data for user code.
    For some simulators, this will also report :term:`HDL` coverage.
    If :envvar:`COVERAGE_RCFILE` is not set, branch coverage is collected
    and files in the cocotb package directory are excluded.

    This needs the :mod:`coverage` Python module to be installed.

    .. versionchanged:: 2.0

        :envvar:`COVERAGE` is renamed to :envvar:`COCOTB_USER_COVERAGE`.

    .. deprecated:: 2.0

        :envvar:`COVERAGE` is a deprecated alias and will be removed.

.. envvar:: COVERAGE_RCFILE

    Location of a configuration file for coverage collection of Python user code
    using the the :mod:`coverage` module.
    See https://coverage.readthedocs.io/en/latest/config.html for documentation of this file.

    If this environment variable is set,
    cocotb will *not* apply its own default coverage collection settings,
    like enabling branch coverage and excluding files in the cocotb package directory.

    .. versionadded:: 1.7

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


.. _pygpi:

PyGPI and the ``cocotb.simulator`` module
-----------------------------------------

The PyGPI is a Python wrapper around the :term:`GPI` (Generic Procedural Interface).

.. envvar:: PYGPI_PYTHON_BIN

    The Python binary in the Python environment to use with cocotb.
    This is set to the result of ``cocotb-config --python-bin`` in the Makefiles and :ref:`Python Runner <howto-python-runner>`.
    You will likely only need to set this variable manually if
    you are using a Python environment other than the currently activated environment,
    or if you are using a :ref:`custom flow <custom-flows>`.

.. envvar:: PYGPI_USERS

    The Python module and callable that starts up the Python cosimulation environment.
    User overloads can be used to enter alternative Python frameworks or to hook existing cocotb functionality.
    The variable is formatted as ``path.to.entry.module:entry_point.function,other_module:other_func``.
    The string before the colon is the Python module to import
    and the string following the colon is the object to call as the entry function.
    Multiple entry points can be specified by separating them with a comma.

    The entry function must be a callable matching this form:

    * ``entry_function(argv: List[str]) -> None``

    .. versionchanged:: 1.8
        ``level`` argument to ``_sim_event`` is no longer passed, it is assumed to be ``SIM_FAIL`` (2).

    .. versionchanged:: 2.0
        The entry-module-level functions ``_sim_event``, ``_log_from_c``, and ``_filter_from_c`` are no longer required.

    .. versionchanged:: 2.0
        Multiple entry points can be specified by separating them with a comma.

    .. versionchanged:: 2.0
        Renamed from ``PYGPI_ENTRY_POINT``.

The ``cocotb.simulator`` module is the Python :keyword:`import`-able interface to the PyGPI.
It should not be considered public API, but is documented here for developers of cocotb.

.. automodule:: cocotb.simulator
    :members:
    :undoc-members:
    :member-order: bysource
    :synopsis: Interface to simulator.
