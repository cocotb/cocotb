############
Introduction
############

What is cocotb?
===============

**Cocotb** is a *coroutine* based *cosimulation* *testbench* environment for testing VHDL/Verilog RTL using Python.

**Cocotb** is completely free, open source (under the `BSD License <http://en.wikipedia.org/wiki/BSD_licenses#3-clause_license_.28.22Revised_BSD_License.22.2C_.22New_BSD_License.22.2C_or_.22Modified_BSD_License.22.29>`_) and hosted on `GitHub <https://github.com/potentialventures/cocotb>`_.

**Cocotb** still requires a simulator to simulate the RTL. Simulators that have been tested and known to work with cocotb:

* Icarus
* Aldec Riviera-PRO
* Synopsys VCS

.. note::
   See the `Simulator Support`_ page for full details of supported simulators.


Why create cocotb?
==================

Verification is the hardest part of realising a working design. Throughout the industry quite a broad spectrum of verification techniques exist, of increasing degrees of complexity:

1. Waveform inspection (non self-checking testbenches)
2. VHDL/Verilog testbenches (self-checking testbenches)
3. File-based testbenches using another language to generate the test-vectors and check the output
4. SystemVerilog or SystemC testbench
5. "e" or UVM based testbench
6. Custom PLI/DPI framework

The EDA tool industry has recognised the limitations of 






How should I use cocotb?
========================

Utilise the simulator features
------------------------------

If you are paying for a simulator, make the most of all the fucntionlity it provides.  Use metrics to asses how verification is progressing. It's surprisingly easy to write a test that doesn't actually test anything.

* Code coverage
* Functional coverage
* Assersions


Structure your testbench
------------------------

Drivers, Monitors, Scoreboards.


Make use of both directed and randomised tests
----------------------------------------------


Use a regression system
-----------------------

`Jenkins <http://jenkins-ci.org/>`_


