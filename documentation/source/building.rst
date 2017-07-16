#######################################
Build options and Environment Variables
#######################################

Make System
===========

Makefiles are provided for a variety of simulators in cocotb/makefiles/simulators.  The common Makefile cocotb/makefiles/Makefile.sim includes the appropriate simulator makefile based on the contents of the SIM variable.

Make Targets
------------

Makefiles define two targets, 'regression' and 'sim', the default target is sim.

Both rules create a results file in the calling directory called 'results.xml'.  This file is a JUnit-compatible output file suitable for use with `Jenkins <http://jenkins-ci.org/>`_. The 'sim' targets unconditionally re-runs the simulator whereas the regression target only re-builds if any dependencies have changed.


Make phases
-----------

Typically the makefiles provided with Cocotb for various simulators use a separate *compile* and *run* target.  This allows for a rapid re-running of a simulator if none of the RTL source files have changed and therefore the simulator does not need to recompile the RTL.



Make Variables
--------------

GUI
~~~

Set this to 1 to enable the GUI mode in the simulator (if supported).



SIM
~~~

Selects which simulator Makefile to use.  Attempts to include a simulator specific makefile from cocotb/makefiles/makefile.$(SIM)


VERILOG_SOURCES
~~~~~~~~~~~~~~~

A list of the Verilog source files to include.


VHDL_SOURCES
~~~~~~~~~~~~~~~

A list of the VHDL source files to include.


COMPILE_ARGS
~~~~~~~~~~~~

Any arguments or flags to pass to the compile stage of the simulation. Only applies to simulators with a separate compilation stage (currently Icarus and VCS).


SIM_ARGS
~~~~~~~~

Any arguments or flags to pass to the execution of the compiled simulation.  Only applies to simulators with a separate compilation stage (currently Icarus, VCS and GHDL).

EXTRA_ARGS
~~~~~~~~~~

Passed to both the compile and execute phases of simulators with two rules, or passed to the single compile and run command for simulators which don't have a distinct compilation stage.

CUSTOM_COMPILE_DEPS
~~~~~~~~~~~~~~~~~~~

Use to add additional dependencies to the compilation target; useful for defining additional rules to run pre-compilation or if the compilation phase depends on files other than the RTL sources listed in **VERILOG_SOURCES** or **VHDL_SOURCES**.

CUSTOM_SIM_DEPS
~~~~~~~~~~~~~~~

Use to add additional dependencies to the simulation target.

COCOTB_NVC_TRACE
~~~~~~~~~~~~~~~~

Set this to 1 to enable display VHPI trace when using nvc VHDL simulator.

Environment Variables
=====================



TOPLEVEL
--------

Used to indicate the instance in the hierarchy to use as the DUT.  If this isn't defined then the first root instance is used.


RANDOM_SEED
-----------

Seed the Python random module to recreate a previous test stimulus.  At the beginning of every test a message is displayed with the seed used for that execution:

.. code-block:: bash
   
    INFO     cocotb.gpi                                  __init__.py:89   in _initialise_testbench           Seeding Python random module with 1377424946


To recreate the same stimulis use the following:

.. code-block:: bash

   make RANDOM_SEED=1377424946



COCOTB_ANSI_OUTPUT
------------------

Use this to override the default behaviour of annotating cocotb output with
ANSI colour codes if the output is a terminal (isatty()).

COCOTB_ANSI_OUTPUT=1 forces output to be ANSI regardless of the type stdout

COCOTB_ANSI_OUTPUT=0 supresses the ANSI output in the log messages


MODULE
------

The name of the module(s) to search for test functions.  Multiple modules can be specified using a comma-separated list.


TESTCASE
--------

The name of the test function(s) to run.  If this variable is not defined cocotb discovers and executes all functions decorated with @cocotb.test() decorator in the supplied modules.

Multiple functions can be specified in a comma-separated list.


