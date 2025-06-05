.. _building:

***************************************
Build Options and Environment Variables
***************************************

Make System
===========

Makefiles are provided for a variety of simulators in :file:`src/cocotb/share/makefiles/simulators`.
The common Makefile :file:`src/cocotb/share/makefiles/Makefile.sim` includes the appropriate simulator Makefile based on the contents of the :make:var:`SIM` variable.

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

Of the environment variables, only :envvar:`COCOTB_TEST_MODULES` is mandatory to be set
(typically done in a makefile or run script), all others are optional.

..
  If you edit the following sections, please also update the "helpmsg" text in ../../src/cocotb_tools/config.py

Cocotb
------

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

.. envvar:: COCOTB_RANDOM_SEED

    Seed the Python random module to recreate a previous test stimulus.
    At the beginning of every test a message is displayed with the seed used for that execution:

    .. code-block:: bash

        INFO     cocotb.gpi                                  __init__.py:89   in _initialise_testbench           Seeding Python random module with 1377424946


    To recreate the same stimuli use the following:

    .. code-block:: bash

       make COCOTB_RANDOM_SEED=1377424946

    See also: :make:var:`COCOTB_PLUSARGS`

    .. versionchanged:: 2.0

        :envvar:`RANDOM_SEED` is renamed to :envvar:`COCOTB_RANDOM_SEED`.

    .. deprecated:: 2.0

        :envvar:`RANDOM_SEED` is a deprecated alias and will be removed.

.. envvar:: COCOTB_PLUSARGS

      "Plusargs" are options that are starting with a plus (``+``) sign.
      They are passed to the simulator and are also available within cocotb as :data:`cocotb.plusargs`.
      In the simulator, they can be read by the Verilog/SystemVerilog system functions
      ``$test$plusargs`` and ``$value$plusargs``.

      The special plusargs ``+ntb_random_seed`` and ``+seed``, if present, are evaluated
      to set the random seed value if :envvar:`COCOTB_RANDOM_SEED` is not set.
      If both ``+ntb_random_seed`` and ``+seed`` are set, ``+ntb_random_seed`` is used.

    .. versionchanged:: 2.0

        :envvar:`PLUSARGS` is renamed to :envvar:`COCOTB_PLUSARGS`.

    .. deprecated:: 2.0

        :envvar:`PLUSARGS` is a deprecated alias and will be removed.

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

    Defaults to ``1``.
    Logs will include simulation time, message type (``INFO``, ``WARNING``, ``ERROR``, ...), logger name, and the log message itself.
    If the value is set to ``0``, the filename and line number where a log function was called will be added between the logger name and the log message.

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

.. envvar:: LIBPYTHON_LOC

    The absolute path to the Python library associated with the current Python installation;
    i.e. ``libpython.so`` or ``python.dll`` on Windows.
    This is determined with ``cocotb-config --libpython`` in cocotb's makefiles.


.. envvar:: COCOTB_TRUST_INERTIAL_WRITES

    Defining this variable enables a mode which allows cocotb to trust that VPI/VHPI/FLI inertial writes are applied properly according to the respective standards.
    This mode can lead to noticeable performance improvements,
    and also includes some behavioral difference that are considered by the cocotb maintainers to be "better".
    Not all simulators handle inertial writes properly, so use with caution.

    This is achieved by *not* scheduling writes to occur at the beginning of the ``ReadWrite`` mode,
    but instead trusting that the simulator's inertial write mechanism is correct.
    This allows cocotb to avoid a VPI callback into Python to apply writes.

    .. note::
        This flag is enabled by default for GHDL and NVC simulators.
        More simulators may enable this flag by default in the future as they are gradually updated to properly apply inertial writes according to the respective standard.

    .. note::
        To test if your simulator behaves correctly with your simulator and version,
        first clone the cocotb github repo and run:

        .. code-block::

            cd tests/test_cases/test_inertial_writes
            make simulator_test SIM=<your simulator here> TOPLEVEL_LANG=<vhdl or verilog>

        If the tests pass, your simulator and version apply inertial writes as expected and you can turn on :envvar:`COCOTB_TRUST_INERTIAL_WRITES`.


Regression Manager
~~~~~~~~~~~~~~~~~~

.. envvar:: COCOTB_TEST_MODULES

    The name of the Python module(s) to search for test functions -
    if your tests are in a file called ``test_mydesign.py``, ``COCOTB_TEST_MODULES`` would be set to ``test_mydesign``.
    Multiple modules can be specified using a comma-separated string.
    For example: ``COCOTB_TEST_MODULES="directed_tests,random_tests,error_injection_tests"``.
    All tests will be run from each specified module in order of the module's appearance in this list.

    The is the only environment variable that is **required** for cocotb, all others are optional.

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

.. envvar:: COCOTB_USER_COVERAGE

    Enable to collect Python coverage data for user code.
    For some simulators, this will also report :term:`HDL` coverage.
    If :envvar:`COCOTB_COVERAGE_RCFILE` is not set, branch coverage is collected
    and files in the cocotb package directory are excluded.

    This needs the :mod:`coverage` Python module to be installed.

    .. versionchanged:: 2.0

        :envvar:`COVERAGE` is renamed to :envvar:`COCOTB_USER_COVERAGE`.

    .. deprecated:: 2.0

        :envvar:`COVERAGE` is a deprecated alias and will be removed.

.. envvar:: COCOTB_COVERAGE_RCFILE

    Location of a configuration file for coverage collection of Python user code
    using the the :mod:`coverage` module.
    See https://coverage.readthedocs.io/en/latest/config.html for documentation of this file.

    If this environment variable is set,
    cocotb will *not* apply its own default coverage collection settings,
    like enabling branch coverage and excluding files in the cocotb package directory.

    .. versionadded:: 1.7

    .. versionchanged:: 2.0

        :envvar:`COVERAGE_RCFILE` is renamed to :envvar:`COCOTB_COVERAGE_RCFILE`.

    .. deprecated:: 2.0

        :envvar:`COVERAGE_RCFILE` is a deprecated alias and will be removed.

.. envvar:: COCOTB_PDB_ON_EXCEPTION

   If defined, cocotb will drop into the Python debugger (:mod:`pdb`) if a test fails with an exception.
   See also the :ref:`troubleshooting-attaching-debugger-python` subsection of :ref:`troubleshooting-attaching-debugger`.


.. envvar:: COCOTB_REWRITE_ASSERTION_FILES

    Select the Python files to apply ``pytest``'s assertion rewriting to.
    This is useful to get more informative assertion error messages in cocotb tests.
    Specify using a space-separated list of file globs, e.g. ``test_*.py testbench_common/**/*.py``.
    Set to the empty string to disable assertion rewriting.
    Defaults to ``*.py`` (all Python files, even third-party modules like ``scipy``).


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

    .. versionchanged:: 1.4
        Support for the custom entry point via ``:`` was added.
        Previously ``:`` was used as a separator between libraries instead of ``,``.

    .. versionchanged:: 1.5
        Library name must be fully specified.
        This allows using relative or absolute paths in library names,
        and loading from libraries that `aren't` prefixed with "lib".
        Paths `should not` contain commas.

PyGPI
-----

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
        ``level`` argument to ``_sim_event`` is no longer passed, it is assumed to be `SIM_FAIL` (2).

    .. versionchanged:: 2.0
        The entry-module-level functions ``_sim_event``, ``_log_from_c``, and ``_filter_from_c`` are no longer required.

    .. versionchanged:: 2.0
        Multiple entry points can be specified by separating them with a comma.

    .. versionchanged:: 2.0
        Renamed from ``PYGPI_ENTRY_POINT``.


Makefile-based Test Scripts
---------------------------

The following variables are makefile variables, not environment variables.

.. make:var:: GUI

      Set this to 1 to enable the GUI mode in the simulator (if supported).

.. make:var:: SIM

      Selects which simulator Makefile to use.  Attempts to include a simulator specific makefile from :file:`src/cocotb/share/makefiles/simulators/makefile.$(SIM)`

.. make:var:: WAVES

      Set this to 1 to enable wave traces dump for the Aldec Riviera-PRO, Mentor Graphics Questa, and Icarus Verilog simulators.
      To get wave traces in Verilator see :ref:`sim-verilator-waveforms`.

.. make:var:: TOPLEVEL_LANG

    Used to inform the makefile scripts which :term:`HDL` language the top-level design element is written in.
    Currently it supports the values ``verilog`` for Verilog or SystemVerilog tops, and ``vhdl`` for VHDL tops.
    This is used by simulators that support more than one interface (:term:`VPI`, :term:`VHPI`, or :term:`FLI`) to select the appropriate interface to start cocotb.

.. make:var:: VHDL_GPI_INTERFACE

    Explicitly sets the simulator interface to use when :make:var:`TOPLEVEL_LANG` is ``vhdl``.
    This includes the initial GPI interface loaded, and :envvar:`GPI_EXTRA` library loaded in mixed language simulations.
    Valid values are ``vpi``, ``vhpi``, or ``fli``.
    Not all simulators support all values; refer to the :ref:`simulator-support` section for details.

    Setting this variable is rarely needed as cocotb chooses a suitable default value depending on the simulator used.

.. make:var:: VERILOG_SOURCES

      A list of the Verilog source files to include.
      Paths can be absolute or relative; if relative, they are interpreted as relative to the location where ``make`` was invoked.

.. make:var:: VERILOG_INCLUDE_DIRS

      A list of the Verilog directories to search for include files.
      Paths can be absolute or relative; if relative, they are interpreted as relative to the location where ``make`` was invoked.

.. make:var:: VHDL_SOURCES

      A list of the VHDL source files to include.
      Paths can be absolute or relative; if relative, they are interpreted as relative to the location where ``make`` was invoked.

.. make:var:: VHDL_SOURCES_<lib>

      A list of the VHDL source files to include in the VHDL library *lib* (currently for GHDL/ModelSim/Questa/Xcelium/Incisive/Riviera-PRO only).

.. make:var:: VHDL_LIB_ORDER

      A space-separated list defining the order in which VHDL libraries should be compiled (needed for ModelSim/Questa/Xcelium/Incisive, GHDL determines the order automatically).

.. make:var:: COMPILE_ARGS

      Any arguments or flags to pass to the compile (analysis) stage of the simulation.

.. make:var:: SIM_ARGS

      Any arguments or flags to pass to the execution of the compiled simulation.

.. make:var:: RUN_ARGS

      Any argument to be passed to the "first" invocation of a simulator that runs via a TCL script.
      One motivating usage is to pass `-noautoldlibpath` to Questa to prevent it from loading the out-of-date libraries it ships with.
      Used by Aldec Riviera-PRO and Mentor Graphics Questa simulator.

.. make:var:: EXTRA_ARGS

      Passed to both the compile and execute phases of simulators with two rules, or passed to the single compile and run command for simulators which don't have a distinct compilation stage.

.. make:var:: SIM_CMD_PREFIX

      Prefix for simulation command invocations.

      This can be used to add environment variables or other commands before the invocations of simulation commands.
      For example, ``SIM_CMD_PREFIX := LD_PRELOAD="foo.so bar.so"`` can be used to force a particular library to load.
      Or, ``SIM_CMD_PREFIX := gdb --args`` to run the simulation with the GDB debugger.

      .. versionadded:: 1.6

.. make:var:: SIM_CMD_SUFFIX

    Suffix for simulation command invocations.
    Typically used to redirect simulator ``stdout`` and ``stderr``:

    .. code-block:: Makefile

        # Prints simulator stdout and stderr to the terminal
        # as well as capture it all in a log file "sim.log".
        SIM_CMD_SUFFIX := 2>&1 | tee sim.log

    .. versionadded:: 2.0

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

      Use to define a scratch directory for use by the simulator. The path is relative to the location where ``make`` was invoked.
      If not provided, the default scratch directory is :file:`sim_build`.

.. envvar:: SCRIPT_FILE

    The name of a simulator script that is run as part of the simulation, e.g. for setting up wave traces.
    You can usually write out such a file from the simulator's GUI.
    This is currently supported for the Mentor Questa, Mentor ModelSim and Aldec Riviera simulators.

.. make:var:: TOPLEVEL_LIBRARY

    The name of the library that contains the :envvar:`COCOTB_TOPLEVEL` module/entity.
    Only supported by the Aldec Riviera-PRO, Aldec Active-HDL, and Siemens EDA Questa simulators.


.. make:var:: PYTHON_BIN

    The path to the Python binary.
    Set to the result of ``cocotb-config --python-bin`` if ``cocotb-config`` is present on the ``PATH``.
    Otherwise defaults to ``python3``.


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
