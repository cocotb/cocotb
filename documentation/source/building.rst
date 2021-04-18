.. _building:

***************************************
Build options and Environment Variables
***************************************

Make System
===========

Makefiles are provided for a variety of simulators in :file:`cocotb/share/makefiles/simulators`.
The common Makefile :file:`cocotb/share/makefiles/Makefile.sim` includes the appropriate simulator Makefile based on the contents of the :make:var:`SIM` variable.

Make Targets
------------

Makefiles defines the targets ``regression`` and ``sim``, the default target is ``sim``.

Both rules create a results file with the name taken from :envvar:`COCOTB_RESULTS_FILE`, defaulting to ``results.xml``.
This file is a xUnit-compatible output file suitable for use with e.g. `Jenkins <https://jenkins.io/>`_.
The ``sim`` targets unconditionally re-runs the simulator whereas the ``regression`` target only re-builds if any dependencies have changed.

In addition, the target ``clean`` can be used to remove build and simulation artifacts.
The target ``help`` lists these available targets and the variables described below.

Make Phases
-----------

Typically the makefiles provided with cocotb for various simulators use a separate ``compile`` and ``run`` target.
This allows for a rapid re-running of a simulator if none of the :term:`RTL` source files have changed and therefore the simulator does not need to recompile the :term:`RTL`.


Variables
=========

The following sections document environment variables and makefile variables according to their owner/consumer.

Of the environment variables, only :envvar:`MODULE` is mandatory to be set
(typically done in a makefile or run script), all others are optional.

..
  If you edit the following sections, please also update the "helpmsg" text in cocotb/config.py

Cocotb
------

.. envvar:: TOPLEVEL

    Use this to indicate the instance in the hierarchy to use as the :term:`DUT`.
    If this isn't defined then the first root instance is used.
    Leading and trailing whitespace are automatically discarded.

    The DUT is available in cocotb tests as a Python object at :data:`cocotb.top`;
    and is also passed to all cocotb tests as the :ref:`first and only parameter <quickstart_creating_a_test>`.

    .. versionchanged:: 2.0 Strip leading and trailing whitespace

.. envvar:: RANDOM_SEED

    Seed the Python random module to recreate a previous test stimulus.
    At the beginning of every test a message is displayed with the seed used for that execution:

    .. code-block:: bash

        INFO     cocotb.gpi                                  __init__.py:89   in _initialise_testbench           Seeding Python random module with 1377424946


    To recreate the same stimuli use the following:

    .. code-block:: bash

       make RANDOM_SEED=1377424946

    See also: :make:var:`PLUSARGS`

.. envvar:: COCOTB_ANSI_OUTPUT

    Use this to override the default behavior of annotating cocotb output with
    ANSI color codes if the output is a terminal (``isatty()``).

    ``COCOTB_ANSI_OUTPUT=1``
       forces output to be ANSI-colored regardless of the type of ``stdout`` or the presence of :envvar:`NO_COLOR`
    ``COCOTB_ANSI_OUTPUT=0``
       suppresses the ANSI color output in the log messages

.. envvar:: NO_COLOR

    From http://no-color.org,

        All command-line software which outputs text with ANSI color added should check for the presence
        of a ``NO_COLOR`` environment variable that, when present (regardless of its value), prevents the addition of ANSI color.

.. envvar:: COCOTB_REDUCED_LOG_FMT

    If defined, log lines displayed in the terminal will be shorter. It will print only
    time, message type (``INFO``, ``WARNING``, ``ERROR``, ...) and the log message itself.

.. envvar:: COCOTB_ATTACH

    In order to give yourself time to attach a debugger to the simulator process before it starts to run,
    you can set the environment variable :envvar:`COCOTB_ATTACH` to a pause time value in seconds.
    If set, cocotb will print the process ID (PID) to attach to and wait the specified time before
    actually letting the simulator run.

.. envvar:: COCOTB_ENABLE_PROFILING

    Enable performance analysis of the Python portion of cocotb. When set, a file :file:`test_profile.pstat`
    will be written which contains statistics about the cumulative time spent in the functions.

    From this, a callgraph diagram can be generated with `gprof2dot <https://github.com/jrfonseca/gprof2dot>`_ and ``graphviz``.

.. envvar:: COCOTB_LOG_LEVEL

    The default logging level to use. This is set to ``INFO`` unless overridden.
    Valid values are ``TRACE``, ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.

    ``TRACE`` is used for internal low-level logging and produces very verbose logs.

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

.. envvar:: MEMCHECK

    HTTP port to use for debugging Python's memory usage.
    When set to e.g. ``8088``, data will be presented at `<http://localhost:8088>`_.

    This needs the :mod:`cherrypy` and :mod:`dowser` Python modules installed.

.. envvar:: LIBPYTHON_LOC

    The absolute path to the Python library associated with the current Python installation;
    i.e. ``libpython.so`` or ``python.dll`` on Windows.
    This is determined with ``cocotb-config --libpython`` in cocotb's makefiles.


Regression Manager
~~~~~~~~~~~~~~~~~~

.. envvar:: MODULE

    The name of the Python module(s) to search for test functions -
    if your tests are in a file called ``test_mydesign.py``, ``MODULE`` would be set to ``test_mydesign``.
    Multiple modules can be specified using a comma-separated list.
    All tests will be run from each specified module in order of the module's appearance in this list.

    The is the only environment variable that is **required** for cocotb, all others are optional.

.. envvar:: TESTCASE

    The name of the test function(s) to run.  If this variable is not defined cocotb
    discovers and executes all functions decorated with the :class:`cocotb.test` decorator in the supplied :envvar:`MODULE` list.

    Multiple test functions can be specified using a comma-separated list.

.. envvar:: COCOTB_RESULTS_FILE

    The file name where xUnit XML tests results are stored. If not provided, the default is :file:`results.xml`.

    .. versionadded:: 1.3

.. envvar:: COVERAGE

    Enable to report Python coverage data. For some simulators, this will also report :term:`HDL` coverage.

    This needs the :mod:`coverage` Python module to be installed.

.. envvar:: COCOTB_PDB_ON_EXCEPTION

   If defined, cocotb will drop into the Python debugger (:mod:`pdb`) if a test fails with an exception.
   See also the :ref:`troubleshooting-attaching-debugger-python` subsection of :ref:`troubleshooting-attaching-debugger`.


Scheduler
~~~~~~~~~

.. envvar:: COCOTB_SCHEDULER_DEBUG

    Enable additional log output of the coroutine scheduler.


GPI
---

.. envvar:: GPI_EXTRA

    A comma-separated list of extra libraries that are dynamically loaded at runtime.
    A function from each of these libraries will be called as an entry point prior to elaboration,
    allowing these libraries to register system functions and callbacks.
    Note that :term:`HDL` objects cannot be accessed at this time.
    An entry point function must be named following a ``:`` separator,
    which follows an existing simulator convention.

    For example:

    * ``GPI_EXTRA=libnameA.so:entryA,libnameB.so:entryB`` will first load ``libnameA.so`` with entry point ``entryA`` , then load ``libnameB.so`` with entry point ``entryB``.

    .. versionchanged:: 1.4.0
        Support for the custom entry point via ``:`` was added.
        Previously ``:`` was used as a separator between libraries instead of ``,``.

    .. versionchanged:: 1.5.0
        Library name must be fully specified.
        This allows using relative or absolute paths in library names,
        and loading from libraries that `aren't` prefixed with "lib".
        Paths `should not` contain commas.


Makefile-based Test Scripts
---------------------------

The following variables are makefile variables, not environment variables.

.. make:var:: GUI

      Set this to 1 to enable the GUI mode in the simulator (if supported).

.. make:var:: SIM

      Selects which simulator Makefile to use.  Attempts to include a simulator specific makefile from :file:`cocotb/share/makefiles/simulators/makefile.$(SIM)`

.. make:var:: WAVES

      Set this to 1 to enable wave traces dump for the Aldec Riviera-PRO and Mentor Graphics Questa simulators.
      To get wave traces in Icarus Verilog see :ref:`sim-icarus-waveforms`.

.. make:var:: TOPLEVEL_LANG

    Used to inform the makefile scripts which :term:`HDL` language the top-level design element is written in.
    Currently it supports the values ``verilog`` for Verilog or SystemVerilog tops, and ``vhdl`` for VHDL tops.
    This is used by simulators that support more than one interface (:term:`VPI`, :term:`VHPI`, or :term:`FLI`) to select the appropriate interface to start cocotb.

    The variable is also made available to cocotb tests conveniently as :data:`cocotb.LANGUAGE`.

.. make:var:: VHDL_GPI_INTERFACE

    Selects a simulator interface to use when :make:var:`TOPLEVEL_LANG` is ``vhdl`` sources are tested.
    This includes the initial GPI interface loaded, and :make:var:`GPI_EXTRA` library loaded in mixed language simulations.
    Valid values are ``vpi``, ``vhpi``, or ``fli``; however not all values are supported by all simulators.

.. make:var:: VERILOG_SOURCES

      A list of the Verilog source files to include.
      Paths can be absolute or relative; if relative, they are interpreted as relative to the Makefile's location.

.. make:var:: VHDL_SOURCES

      A list of the VHDL source files to include.
      Paths can be absolute or relative; if relative, they are interpreted as relative to the Makefile's location.

.. make:var:: VHDL_SOURCES_<lib>

      A list of the VHDL source files to include in the VHDL library *lib* (currently for GHDL/ModelSim/Questa only).

.. make:var:: COMPILE_ARGS

      Any arguments or flags to pass to the compile stage of the simulation.

.. make:var:: SIM_ARGS

      Any arguments or flags to pass to the execution of the compiled simulation.

.. make:var:: RUN_ARGS

      Any argument to be passed to the "first" invocation of a simulator that runs via a TCL script.
      One motivating usage is to pass `-noautoldlibpath` to Questa to prevent it from loading the out-of-date libraries it ships with.
      Used by Aldec Riviera-PRO and Mentor Graphics Questa simulator.

.. make:var:: EXTRA_ARGS

      Passed to both the compile and execute phases of simulators with two rules, or passed to the single compile and run command for simulators which don't have a distinct compilation stage.

.. make:var:: PLUSARGS

      "Plusargs" are options that are starting with a plus (``+``) sign.
      They are passed to the simulator and are also available within cocotb as :data:`cocotb.plusargs`.
      In the simulator, they can be read by the Verilog/SystemVerilog system functions
      ``$test$plusargs`` and ``$value$plusargs``.

      The special plusargs ``+ntb_random_seed`` and ``+seed``, if present, are evaluated
      to set the random seed value if :envvar:`RANDOM_SEED` is not set.
      If both ``+ntb_random_seed`` and ``+seed`` are set, ``+ntb_random_seed`` is used.

.. make:var:: COCOTB_HDL_TIMEUNIT

      The default time unit that should be assumed for simulation when not specified by modules in the design.
      If this isn't specified then it is assumed to be ``1ns``.
      Allowed values are 1, 10, and 100.
      Allowed units are ``s``, ``ms``, ``us``, ``ns``, ``ps``, ``fs``.

      .. versionadded:: 1.3

.. make:var:: COCOTB_HDL_TIMEPRECISION

      The default time precision that should be assumed for simulation when not specified by modules in the design.
      If this isn't specified then it is assumed to be ``1ps``.
      Allowed values are 1, 10, and 100.
      Allowed units are ``s``, ``ms``, ``us``, ``ns``, ``ps``, ``fs``.

      .. versionadded:: 1.3

.. make:var:: CUSTOM_COMPILE_DEPS

      Use to add additional dependencies to the compilation target; useful for defining additional rules to run pre-compilation or if the compilation phase depends on files other than the :term:`RTL` sources listed in :make:var:`VERILOG_SOURCES` or :make:var:`VHDL_SOURCES`.

.. make:var:: CUSTOM_SIM_DEPS

      Use to add additional dependencies to the simulation target.

.. make:var:: SIM_BUILD

      Use to define a scratch directory for use by the simulator. The path is relative to the Makefile location.
      If not provided, the default scratch directory is :file:`sim_build`.

.. envvar:: SCRIPT_FILE

    The name of a simulator script that is run as part of the simulation, e.g. for setting up wave traces.
    You can usually write out such a file from the simulator's GUI.
    This is currently supported for the Mentor Questa, Mentor ModelSim and Aldec Riviera simulators.


Library Build Process
---------------------

You can pass additional options to the library build process
(which is usually happening as part of the installation with ``pip``) using the
`conventional variables <https://www.gnu.org/software/make/manual/html_node/Catalogue-of-Rules.html>`_
for C and C++ compilation and linking:
`CFLAGS`,
`CPPFLAGS`,
and
`LDFLAGS`.

..
   `CXXFLAGS`, `LDLIBS` are not supported by distutils/pip


Internal Variables
------------------

The following variables are used for cocotb internals.
They may change at any time, and users should not rely on them.

.. envvar:: COCOTB_PY_DIR

    Path to the directory containing the cocotb Python package in the :file:`cocotb` subdirectory.

.. envvar:: COCOTB_SHARE_DIR

    Path to the directory containing the cocotb Makefiles and simulator libraries in the subdirectories
    :file:`lib`, :file:`include`, and :file:`makefiles`.

.. envvar:: COCOTB_LIBRARY_COVERAGE

   Enable code coverage collection for cocotb internals.
   When set, a file :file:`.coverage.cocotb` will be written which contains statistics about the code coverage.
   This is mainly useful for cocotb's own Continuous Integration setup.

..
   TODO

   Build Defines
   -------------

   SINGLETON_HANDLES
   PYTHON_SO_LIB

   simulator sim defines
