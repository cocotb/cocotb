.. _building:

*******************************************
Makefile-based Build System and Test Runner
*******************************************

cocotb has traditionally provided a Makefile-based design build system and test runner.
The build system should be *sufficient*, but may not be easy to use for more serious projects.

Makefiles are provided for a variety of simulators in :file:`src/cocotb-tools/makefiles/simulators`.

The common Makefile :file:`src/cocotb-tools/makefiles/Makefile.sim` includes the appropriate simulator Makefile based on the contents of the :make:var:`SIM` variable.

Make Targets
============

Makefiles defines the targets ``regression`` and ``sim``, the default target is ``sim``.

Both rules create a results file with the name taken from :envvar:`COCOTB_RESULTS_FILE`, defaulting to ``results.xml``.
This file is a xUnit-compatible output file suitable for use with e.g. `Jenkins <https://jenkins.io/>`_.
The ``sim`` targets unconditionally re-runs the simulator whereas the ``regression`` target only re-builds if any dependencies have changed.

In addition, the target ``clean`` can be used to remove build and simulation artifacts.
The target ``help`` lists these available targets and the variables described below.

Make Phases
===========

Typically the makefiles provided with cocotb for various simulators use a separate ``compile`` and ``run`` target.
This allows for a rapid re-running of a simulator if none of the :term:`RTL` source files have changed and therefore the simulator does not need to recompile the :term:`RTL`.

Make Variables
==============

..
  If you edit the following sections, please also update the "helpmsg" text in src/cocotb_tools/config.py

.. make:var:: GUI

      Set this to 1 to enable the GUI mode in the simulator (if supported).

.. make:var:: SIM

      In the makefile flow, selects which simulator Makefile to use.
      Attempts to include a simulator specific makefile from :file:`src/cocotb/share/makefiles/simulators/makefile.$(SIM)`

      In the :ref:`Python Runner <howto-python-runner>` flow,
      selects the :ref:`Simulator Runner <api-runner-sim>` to use.

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
      Used by Riviera-PRO and Questa simulator.

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

The :envvar:`COCOTB_TOPLEVEL` variable is also often used by the Makefile-based build and runner system.
