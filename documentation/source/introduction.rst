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

Throughout the industry quite a broad spectrum of verification techniques exist, of increasing degrees of complexity:

1. Waveform inspection (non self-checking testbenches)
2. VHDL/Verilog testbenches (self-checking testbenches)
3. File-based testbenches using another language to generate the test-vectors and check the output
4. SystemVerilog or SystemC testbench
5. "e" or UVM based testbench
6. Custom PLI/DPI framework

Verification is the hardest part of realising a working design. 
The EDA industry has invested heavily in helping us verify designs, 
adding software contructs to verilog when creating SystemVerilog, 
mandating that simulators need to implement constrain solvers, 
converging on UVM as a standard methodology. Why is this inadequate?

Fundamentally the process of verification is writing software, specifically software to test a design, 
where the design happens to be synthesisable into real hardware. If VHDL, Verilog or 
SystemVerilog excelled as software languages would there not be examples of their use outside of EDA?


UVM
---

UVM is a prime example of how the EDA industry solves a problem and the solution isn't pretty. While the ideas driving
UVM are valid (defining a common testbench structure, promoting code re-use, using constrained-random testing) and good, 
the outcome is a step backwards for the following reasons:

UVM is ugly
^^^^^^^^^^^

Given the rapid progress being made in software development and evolution of new languages, creating a framework that requires
so much boilerplate and relies so heavily on macros is actually impressive! This highlights why bashing SystemVerilog
to behave like a software language is midguided.


UVM is niche
^^^^^^^^^^^^

UVM is a niche within an already highly specialised area. Finding good UVM guys is difficult and expensive.
In the time it takes you to find 1 UVM developer I can hire 3 Python developers (and probabaly for the same total cost).


UVM is expensive
^^^^^^^^^^^^^^^^

I have to pay for a simulator.  I then have to pay more to enable SystemVerilog verification features. I have to hire expensive people. This is good for EDA vendors but bad for innovation.


What makes cocotb any better?
-----------------------------

Ranting aside, what is the idea behind cocotb any why is it different?

Use the right tool for the job
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In cocotb VHDL/Verilog/SystemVerilog are only used for the synthesisable design. All verification is done using Python.

Python is ideal for rapid development of complex systems, integrating multiple languages, 
utilising the capabilites of the standard libraries and extensions like 
`constraint solvers <https://code.google.com/p/or-tools/>`_ and `packet parsing/generation <http://www.secdev.org/projects/scapy/>`_ libraries.


Because Python is an interpreted language, I can actually edit my tests and re-run them without having to recompile the design or even exit the simulator GUI.


Lower the overhead of creating a test
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using cocotb the DUT hangs in "free space" in the simulator, you don't even have to create an instance and wire it up. 
Tests themselves are very terse and easy to create. This lower overhead encourages creation of regression tests even for
sub-blocks where usually the overhead of writing a testbench is too onerous.


Open verification to a wider audience
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ASIC/FPGA designs always involve some software development. 
Often the hardware team is responsible for creating and verifying the RTL with little interaction 
with the software team although as the boundaries blur the software teams are tending to get more involved (often with exclamations of `WTF?! <http://www.osnews.com/story/19266/WTFs_m>`_).
Cocotb encourages more people to get more involved in RTL design by lowering the barrier to entry. Python is a common language accessible to a larger audience.




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


