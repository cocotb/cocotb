############
Introduction
############

What is cocotb?
===============

**Cocotb** is a *coroutine* based *cosimulation* *testbench* environment for testing VHDL/Verilog RTL using `Python <http://python.org>`_.

**Cocotb** is completely free, open source (under the `BSD License <http://en.wikipedia.org/wiki/BSD_licenses#3-clause_license_.28.22Revised_BSD_License.22.2C_.22New_BSD_License.22.2C_or_.22Modified_BSD_License.22.29>`_) and hosted on `GitHub <https://github.com/potentialventures/cocotb>`_.

**Cocotb** requires a simulator to simulate the RTL. Simulators that have been tested and known to work with cocotb:

* Icarus Verilog
* Synopsys VCS
* Aldec Riviera-PRO
* Cadence Incisive
* Mentor Modelsim

**Cocotb** was developed by `Potential Ventures <http://potential.ventures>`_ with the support of `Solarflare Communications Ltd <http://www.solarflare.com/>`_ and contributions from Gordon McGregor and Finn Grimwood.

**Cocotb** can be used live in a web-browser on the excellent `EDA Playground <http://www.edaplayground.com>`_.


How is cocotb different?
------------------------

**Cocotb** encourages the same philosophy of design re-use and randomised testing as UVM, however is implemented in Python rather than SystemVerilog.

In cocotb VHDL/Verilog/SystemVerilog are only used for the synthesisable design. All verification is done using Python which has various advantages over using SystemVerilog or VHDL for verification:

* Writing Python is **fast** - it's a very productive language
* It's **easy** to interface to other languages from Python
* Python has a huge library of existing code to **re-use** like `packet generation <http://www.secdev.org/projects/scapy/>`_ libraries.
* Python is **interpreted**. Tests can be edited and re-run them without having to recompile the design or exit the simulator GUI.
* Python is **popular** - far more engineers know Python than SystemVerilog or VHDL

**Cocotb** was specifically designed to lower the overhead of creating a test.

**Cocotb** has built-in support for integrating with the `Jenkins <http://jenkins-ci.org/>`_ continuous integration system.

**Cocotb** automatically discovers tests so that no additional step is required to add a test to a regression.


How does Cocotb work
====================

Overview
--------

A typical cocotb testbench requires no additional RTL code. The Design Under Test (DUT) is instantiated as the toplevel in the simulator without any wrapper code. Cocotb drives stimulus onto the inputs to the DUT (or further down the hierarchy) and monitors the outputs directly from Python.


.. image:: diagrams/svg/cocotb_overview.svg

A test is simply a Python function.  At any given time either the simulator is advancing time or the Python code is executing.  The **yield** keyword is used to indicate when to pass control of execution back to the simulator.  A test can spawn multiple coroutines, allowing for independent flows of execution.

