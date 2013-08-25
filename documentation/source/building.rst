#######################################
Build options and Environment Variables
#######################################

Make System
===========


Environment Variables
=====================



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

COCOTB_ANDI_OUTPUT=0 supresses the ANSI output in the log messages


MODULE
------

The name of the module(s) to search for test functions.  Multiple modules can be specified using a comma-separated list.


TESTCASE
--------

The name of the test function(s) to run.  If this variable is not defined cocotb discovers and executes all functions decorated with @cocotb.test() decorator in the supplied modules.

Multiple functions can be specified in a comma-separated list.

