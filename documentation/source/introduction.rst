############
Introduction
############

What is cocotb?
===============

**Cocotb** is a *coroutine* based *cosimulation* *testbench* environment for testing VHDL/Verilog RTL using Python.

**Cocotb** is completely free, open source (under the `BSD License <http://en.wikipedia.org/wiki/BSD_licenses#3-clause_license_.28.22Revised_BSD_License.22.2C_.22New_BSD_License.22.2C_or_.22Modified_BSD_License.22.29>`_) and hosted on `GitHub <https://github.com/potentialventures/cocotb>`_.

**Cocotb** requires a simulator to simulate the RTL. Simulators that have been tested and known to work with cocotb:

* Icarus Verilog
* Synopsys VCS
* Aldec Riviera-PRO
* Mentor Questa
* Cadance Incisive

**Cocotb** was developed by Potential Ventures with the support of `Solarflare Communications Ltd <http://www.solarflare.com/>`_ and contributions from Gordon McGregor and Finn Grimwood.



How is cocotb different?
------------------------

Cocotb encourages the same philosophy of design re-use and randomised testing as UVM, however is implemented in Python rather than SystemVerilog.

In cocotb VHDL/Verilog/SystemVerilog are only used for the synthesisable design. All verification is done using Python which is ideal for rapid development of complex systems and integrating multiple languages. Using Python has various advantages over using SystemVerilog or VHDL for verification:

* Writing Python is **fast** - it's a very productive language
* It's **easy** to interface to other languages from Python
* Python has a huge library of existing code to **re-use** like `packet parsing/generation <http://www.secdev.org/projects/scapy/>`_ libraries.
* Python is **interpreted**. Tests can be edited and re-run them without having to recompile the design or exit the simulator GUI.
* Python is **popular** - far more engineers know Python than SystemVerilog or VHDL


Lower the overhead of creating a test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using cocotb the DUT hangs in "free space" in the simulator, you don't even have to create an instance and wire it up. 
Tests themselves are very terse and easy to create. This lower overhead encourages creation of regression tests even for
sub-blocks where usually the overhead of writing a testbench is too onerous.


Open verification to a wider audience
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ASIC/FPGA designs always involve some software development. 
Often the hardware team is responsible for creating and verifying the RTL with little interaction between them and the software team. As the boundaries blur the software teams becoming more involved in the RTL and Cocotb encourages this by lowering the barrier to entry. Python is a common language accessible to a larger audience providing a common ground for RTL, verification and software developers.



How should I use cocotb?
------------------------

Verifying using Cocotb is similar to any other verification environment and the usual best-practice advice applies:



Utilise the simulator features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are paying for a simulator, make the most of all the fucntionlity it provides.  Use metrics to asses how verification is progressing. It's surprisingly easy to write a test that doesn't actually test anything.  Use *code coverage* and *functional coverage* to track verification progress, embed assersions to validate behaviour.


Structure your testbench
^^^^^^^^^^^^^^^^^^^^^^^^

Cocotb provides base classes for `Drivers`_, `Monitors`_ and `Scoreboards`_. Any moderately complex testbench should build on these abstractions.

Drivers provide an mechanism for driving a transaction onto a bus in the simulator by waggling pins typically over one or more clock cycles.

Monitors perform the inverse function of drivers, reconstructing transactions by observing bus behaviour.

A scoreboard is a way to validate that the DUT is behaving correctly (in addition to assertions and protocol checkers in any bus models).  Typically this is by comparing the transactions seen by the monitors with expected output based on a software model.


Write directed and randomised tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Directed tests are very useful in the initial phases of development and when attempting to recreate particular bugs or behaviour. Cocotb encourages the use of short directed tests forming a regression since all tests are automatically included in a regression using test auto-discovery.


Test Driven Development
^^^^^^^^^^^^^^^^^^^^^^^


Use a regression system
^^^^^^^^^^^^^^^^^^^^^^^

`Jenkins <http://jenkins-ci.org/>`_


Getting Started
===============

**Cocotb** can be used live in a web-browser on the excellent `EDA Playground <http://www.edaplayground.com>`_.

