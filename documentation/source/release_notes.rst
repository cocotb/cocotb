#############
Release Notes
#############

All releases are available from the `GitHub Releases Page <https://github.com/cocotb/cocotb/releases>`_.

cocotb 1.2
==========

Released on 24 July 2019

New features
------------

- cocotb is now built as Python package and installable through pip. (:pr:`517`, :pr:`799`, :pr:`800`, :pr:`803`, :pr:`805`)
- Support for async functions and generators was added (Python 3 only). Please have a look at :ref:`async_functions` for an example how to use this new feature.
- VHDL block statements can be traversed. (:pr:`850`)
- Support for Python 3.7 was added.

Notable changes and bug fixes
-----------------------------

- The heart of cocotb, its scheduler, is now even more robust. Many small bugs, inconsistencies and unreliable behavior have been ironed out.
- Exceptions are now correctly propagated between coroutines, giving users the "natural" behavior they'd expect with exceptions. (:pr:`633`)
- The ``setimmediatevalue()`` function now works for values larger than 32 bit. (:pr:`768`)
- The documentation was cleaned up, improved and extended in various places, making it more consistent and complete.
- Tab completion in newer versions of IPython is fixed. (:pr:`825`)
- Python 2.6 is officially not supported any more. cocotb supports Python 2.7 and Python 3.5+.
- The cocotb GitHub project moved from ``potentialventures/cocotb`` to ``cocotb/cocotb``. 
  Redirects for old URLs are in place.

Known issues
------------

- Depending on your simulation, cocotb 1.2 might be roughly 20 percent slower than cocotb 1.1.
  Much of the work in this release cycle went into fixing correctness bugs in the scheduler, sometimes at the cost of performance.
  We are continuing to investigate this in issue :issue:`961`.
  Independent of the cocotb version, we recommend using the latest Python 3 version, which is shown to be significantly faster than previous Python 3 versions, and slightly faster than Python 2.7.

Please have a look at the `issue tracker <https://github.com/cocotb/cocotb/issues>`_ for more outstanding issues and contribution opportunities.

cocotb 1.1
==========

Released on 24 Jan 2019.

This release is the result of four years of work with too many bug fixes, improvements and refactorings to name them all.
Please have a look at the release announcement `on the mailing list <https://lists.librecores.org/pipermail/cocotb/2019-January/000053.html>`_ for further information.

cocotb 1.0
==========

Released on 15 Feb 2015.

New features
------------

- FLI support for Modelsim
- Mixed Language, Verilog and VHDL
- Windows
- 300% performance improvement with VHPI interface
- Wavedrom support for wave diagrams.


cocotb 0.4
==========

Released on 25 Feb 2014.


New features
------------
- Issue :issue:`101`: Implement Lock primitive to support mutex
- Issue :issue:`105`: Compatibility with Aldec Riviera-Pro
- Issue :issue:`109`: Combine multiple results.xml into a single results file
- Issue :issue:`111`: XGMII drivers and monitors added
- Issue :issue:`113`: Add operators to BinaryValue class
- Issue :issue:`116`: Native VHDL support by implementing VHPI layer
- Issue :issue:`117`: Added AXI4-Lite Master BFM

Bugs fixed
----------

- Issue :issue:`100`: Functional bug in endian_swapper example RTL
- Issue :issue:`102`: Only 1 coroutine wakes up of multiple coroutines wait() on an Event
- Issue :issue:`114`: Fix build issues with Cadence IUS simulator

New examples
------------
- Issue :issue:`106`: TUN/TAP example using ping


cocotb 0.3
==========

Released on 27 Sep 2013.

This contains a raft of fixes and feature enhancements.


cocotb 0.2
==========

Released on 19 Jul 2013.

New features
------------
- Release 0.2 supports more simulators and increases robustness over 0.1.
- A centralised installation is now supported (see documentation) with supporting libraries build when the simulation is run for the first time.


cocotb 0.1
==========

Released on 9 Jul 2013.

- The first release of cocotb.
- Allows installation and running against Icarus, VCS, Aldec simulators.
