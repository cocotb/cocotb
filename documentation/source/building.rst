#######################################
Build options and Environment Variables
#######################################

Make System
===========

Makefiles are provided for a variety of simulators in :file:`cocotb/share/makefiles/simulators`.
The common Makefile :file:`cocotb/share/makefiles/Makefile.sim` includes the appropriate simulator Makefile based on the contents of the ``SIM`` variable.

Make Targets
------------

Makefiles define two targets, ``regression`` and ``sim``, the default target is ``sim``.

Both rules create a results file with the name taken from :envvar:`COCOTB_RESULTS_FILE`, defaulting to ``results.xml``.  This file is a JUnit-compatible output file suitable for use with `Jenkins <https://jenkins.io/>`_. The ``sim`` targets unconditionally re-runs the simulator whereas the ``regression`` target only re-builds if any dependencies have changed.

Make Phases
-----------

Typically the makefiles provided with Cocotb for various simulators use a separate ``compile`` and ``run`` target.  This allows for a rapid re-running of a simulator if none of the RTL source files have changed and therefore the simulator does not need to recompile the RTL.



Make Variables
--------------

.. glossary::

    ``GUI``
      Set this to 1 to enable the GUI mode in the simulator (if supported).

    ``SIM``
      Selects which simulator Makefile to use.  Attempts to include a simulator specific makefile from :file:`cocotb/share/makefiles/makefile.$(SIM)`

    ``VERILOG_SOURCES``
      A list of the Verilog source files to include.

    ``VHDL_SOURCES``
      A list of the VHDL source files to include.

    ``VHDL_SOURCES_lib``
      A list of the VHDL source files to include in the VHDL library *lib* (currently GHDL only).

    ``COMPILE_ARGS``
      Any arguments or flags to pass to the compile stage of the simulation.

    ``SIM_ARGS``
      Any arguments or flags to pass to the execution of the compiled simulation.

    ``EXTRA_ARGS``
      Passed to both the compile and execute phases of simulators with two rules, or passed to the single compile and run command for simulators which don't have a distinct compilation stage.

    ``CUSTOM_COMPILE_DEPS``
      Use to add additional dependencies to the compilation target; useful for defining additional rules to run pre-compilation or if the compilation phase depends on files other than the RTL sources listed in :term:`VERILOG_SOURCES` or :term:`VHDL_SOURCES`.

    ``CUSTOM_SIM_DEPS``
      Use to add additional dependencies to the simulation target.

    ``COCOTB_NVC_TRACE``
      Set this to 1 to enable display of VHPI traces when using the nvc VHDL simulator.

    ``SIM_BUILD``
      Use to define a scratch directory for use by the simulator. The path is relative to the Makefile location.
      If not provided, the default scratch directory is :file:`sim_build`.


Environment Variables
=====================

.. envvar:: TOPLEVEL

    Used to indicate the instance in the hierarchy to use as the DUT.
    If this isn't defined then the first root instance is used.

.. envvar:: RANDOM_SEED

    Seed the Python random module to recreate a previous test stimulus.
    At the beginning of every test a message is displayed with the seed used for that execution:

    .. code-block:: bash

        INFO     cocotb.gpi                                  __init__.py:89   in _initialise_testbench           Seeding Python random module with 1377424946


    To recreate the same stimuli use the following:

    .. code-block:: bash

       make RANDOM_SEED=1377424946

.. envvar:: COCOTB_ANSI_OUTPUT

    Use this to override the default behaviour of annotating Cocotb output with
    ANSI colour codes if the output is a terminal (``isatty()``).

    ``COCOTB_ANSI_OUTPUT=1`` forces output to be ANSI regardless of the type stdout

    ``COCOTB_ANSI_OUTPUT=0`` supresses the ANSI output in the log messages

.. envvar:: COCOTB_REDUCED_LOG_FMT

    If defined, log lines displayed in terminal will be shorter. It will print only
    time, message type (``INFO``, ``WARNING``, ``ERROR``) and log message.

.. envvar:: MODULE

    The name of the module(s) to search for test functions.  Multiple modules can be specified using a comma-separated list.

.. envvar:: TESTCASE

    The name of the test function(s) to run.  If this variable is not defined Cocotb
    discovers and executes all functions decorated with the :class:`cocotb.test` decorator in the supplied modules.

    Multiple functions can be specified in a comma-separated list.

.. envvar:: COCOTB_RESULTS_FILE

    The filename where XML tests results are stored. If not provided, the default is :file:`results.xml`.

    .. versionadded:: 1.3


Additional Environment Variables
--------------------------------

.. envvar:: COCOTB_ATTACH

    In order to give yourself time to attach a debugger to the simulator process before it starts to run,
    you can set the environment variable :envvar:`COCOTB_ATTACH` to a pause time value in seconds.
    If set, Cocotb will print the process ID (PID) to attach to and wait the specified time before
    actually letting the simulator run.

.. envvar:: COCOTB_ENABLE_PROFILING

    Enable performance analysis of the Python portion of Cocotb. When set, a file :file:`test_profile.pstat`
    will be written which contains statistics about the cumulative time spent in the functions.

    From this, a callgraph diagram can be generated with `gprof2dot <https://github.com/jrfonseca/gprof2dot>`_ and ``graphviz``.
    See the ``profile`` Make target in the ``endian_swapper`` example on how to set this up.

.. envvar:: COCOTB_HOOKS

    A comma-separated list of modules that should be executed before the first test.
    You can also use the :class:`cocotb.hook` decorator to mark a function to be run before test code.

.. envvar:: COCOTB_LOG_LEVEL

    Default logging level to use. This is set to ``INFO`` unless overridden.

.. envvar:: COCOTB_RESOLVE_X

    Defines how to resolve bits with a value of ``X``, ``Z``, ``U`` or ``W`` when being converted to integer.
    Valid settings are:

    ``VALUE_ERROR``
       raise a :exc:`ValueError` exception
    ``ZEROS``
       resolve to ``0``
    ``ONES``
       resolve to ``1``
    ``RANDOM``
       randomly resolve to a ``0`` or a ``1``

    Set to ``VALUE_ERROR`` by default.

.. envvar:: COCOTB_SCHEDULER_DEBUG

    Enable additional log output of the coroutine scheduler.

.. envvar:: COVERAGE

    Enable to report python coverage data. For some simulators, this will also report HDL coverage.

    This needs the :mod:`coverage` python module

.. envvar:: MEMCHECK

    HTTP port to use for debugging Python's memory usage.
    When set to e.g. ``8088``, data will be presented at `<http://localhost:8088>`_.

    This needs the :mod:`cherrypy` and :mod:`dowser` Python modules installed.

.. envvar:: COCOTB_PY_DIR

    Path to the directory containing the cocotb Python package in the ``cocotb`` subdirectory.

.. envvar:: COCOTB_SHARE_DIR

    Path to the directory containing the cocotb Makefiles and simulator libraries in the subdirectories ``lib``, ``include``, and ``makefiles``.

.. envvar:: VERSION

    The version of the Cocotb installation. You probably don't want to modify this.
