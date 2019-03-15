############
Introduction
############

What is cocotb?
===============

**cocotb** is a *COroutine* based *COsimulation* *TestBench* environment for verifying VHDL/Verilog RTL using `Python <https://www.python.org>`_.

cocotb is completely free, open source (under the `BSD License <https://en.wikipedia.org/wiki/BSD_licenses#3-clause_license_(%22BSD_License_2.0%22,_%22Revised_BSD_License%22,_%22New_BSD_License%22,_or_%22Modified_BSD_License%22)>`_) and hosted on `GitHub <https://github.com/cocotb/cocotb>`_.

cocotb requires a simulator to simulate the RTL. Simulators that have been tested and known to work with cocotb:

Linux Platforms

* `Icarus Verilog <http://iverilog.icarus.com/>`_
* `GHDL <https://ghdl.free.fr/>`_
* `Aldec <https://www.aldec.com/>`_ Riviera-PRO
* `Synopsys <https://www.synopsys.com/>`_ VCS
* `Cadence <https://www.cadence.com/>`_ Incisive
* `Mentor <https://www.mentor.com/>`_ Modelsim (DE and SE)

Windows Platform

* `Icarus Verilog <http://iverilog.icarus.com/>`_
* `Aldec <https://www.aldec.com/>`_ Riviera-PRO
* `Mentor <https://www.mentor.com/>`_ Modelsim (DE and SE)

A (possibly older) version of cocotb can be used live in a web-browser using `EDA Playground <https://www.edaplayground.com>`_.



How is cocotb different?
========================


cocotb encourages the same philosophy of design re-use and randomised testing as UVM, however is implemented in Python rather than SystemVerilog.

In cocotb, VHDL/Verilog/SystemVerilog are only used for the synthesisable design.

cocotb has built-in support for integrating with the `Jenkins <https://jenkins.io/>`_ continuous integration system.

cocotb was specifically designed to lower the overhead of creating a test.

cocotb automatically discovers tests so that no additional step is required to add a test to a regression.

All verification is done using Python which has various advantages over using SystemVerilog or VHDL for verification:

* Writing Python is **fast** - it's a very productive language
* It's **easy** to interface to other languages from Python
* Python has a huge library of existing code to **re-use** like `packet generation <https://www.secdev.org/projects/scapy/>`_ libraries.
* Python is **interpreted**. Tests can be edited and re-run them without having to recompile the design or exit the simulator GUI.
* Python is **popular** - far more engineers know Python than SystemVerilog or VHDL


How does cocotb work?
=====================

Overview
--------

A typical cocotb testbench requires no additional RTL code.
The Design Under Test (DUT) is instantiated as the toplevel in the simulator without any wrapper code.
cocotb drives stimulus onto the inputs to the DUT (or further down the hierarchy) and monitors the outputs directly from Python.


.. image:: diagrams/svg/cocotb_overview.svg

A test is simply a Python function.
At any given time either the simulator is advancing time or the Python code is executing.
The ``yield`` keyword is used to indicate when to pass control of execution back to the simulator.
A test can spawn multiple coroutines, allowing for independent flows of execution.


Contributors
============

cocotb was developed by `Potential Ventures <https://potential.ventures>`_ with the support of
`Solarflare Communications Ltd <https://www.solarflare.com/>`_
and contributions from Gordon McGregor and Finn Grimwood
(see `contributers <https://github.com/cocotb/cocotb/graphs/contributors>`_ for the full list of contributions).

We also have a list of talks and papers, libraries and examples at our wiki page
`Further Resources <https://github.com/cocotb/cocotb/wiki/Further-Resources>`_.
Feel free to add links to cocotb-related content that we are still missing!
