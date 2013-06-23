############
Introduction
############

What is cocotb?
===============

**Cocotb** is a *coroutine* based *cosimulation* *testbench* environment for testing VHDL/Verilog RTL using Python.

**Cocotb** is completely free, open source (under the `BSD License <http://en.wikipedia.org/wiki/BSD_licenses#3-clause_license_.28.22Revised_BSD_License.22.2C_.22New_BSD_License.22.2C_or_.22Modified_BSD_License.22.29>`_) and hosted on `GitHub <https://github.com/potentialventures/cocotb>`_.
Cocotb still requires a simulator to simulate the RTL. Simulators that have been tested and known to work with cocotb:

* Icarus
* Aldec Riviera-PRO
* Synopsys VCS

See the :doc:`Simulator Support` page for full details of supported simulators and any gotchas.

Why create cocotb?
==================

Verification is the hardest part of realising a working design. Throughout the industry quite a broad spectrum of verification techniques exist, of varying degrees of complexity:

#. Waveform inspection (non self-checking testbenches)
#. VHDL/Verilog testbenches
#. File-based testbenches using another language to generate the test-vectors and check the output
#. SystemVerilog or SystemC testbench
#. UVM based testbench
#. Custom PLI/DPI framework


How should I use cocotb?
========================

Utilise the simulator features
------------------------------

If you are paying for a simulator, make the most of all the fucntionlity it provides.

* Code coverage
* Functional coverage
* Assersions

