############
Installation
############

Get the Source
==============

Source can be obtained as a tar ball for the current `release <https://github.com/potentialventures/cocotb/tree/v0.3>`_.

Or by cloning the repository `git@github.com:potentialventures/cocotb.git`

There are two supported installation options for Cocotb, standalone or centralised.

Standalone Usage
================

Simply check out the code and hit make at the root of the tree. This will run the test cases and exampkles against `Icarus <http://iverilog.icarus.com/>`_.

The list of supported simulators for the version you have can be found by *make help*.

Centralised Usage
=================

A build can be installed in a centralised location with *make install FULL_INSTALL_DIR=<dir>*. This will also generate an uninstall script.
