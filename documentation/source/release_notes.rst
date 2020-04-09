*************
Release Notes
*************

All releases are available from the `GitHub Releases Page <https://github.com/cocotb/cocotb/releases>`_.

.. include:: generated/master-notes.rst

.. towncrier release notes start

cocotb 1.3.1
============

Released on 15 March 2020

Notable changes and bug fixes
-----------------------------
- The Makefiles for the Aldec Riviera and Cadence Incisive simulators have been fixed to use the correct name of the VHPI library (``libcocotbvhpi``).
  This bug prevented VHDL designs from being simulated, and was a regression in 1.3.0. (:pr:`1472`)

cocotb 1.3.0
============

Released on 08 January 2020

This will likely be the last release to support Python 2.7.

New features
------------

- Initial support for the :ref:`sim-verilator` simulator (version 4.020 and above).
  The integration of Verilator into cocotb is not yet as fast or as powerful as it is for other simulators.
  Please use the latest version of Verilator, and `report bugs <https://github.com/cocotb/cocotb/issues/new>`_ if you experience problems.
- New makefile variables :make:var:`COCOTB_HDL_TIMEUNIT` and :make:var:`COCOTB_HDL_TIMEPRECISION` for setting the default time unit and precision that should be assumed for simulation when not specified by modules in the design. (:pr:`1113`)
- New ``timeout_time`` and ``timeout_unit`` arguments to :func:`cocotb.test`, for adding test timeouts. (:pr:`1119`)
- :func:`cocotb.triggers.with_timeout`, for a shorthand for waiting for a trigger with a timeout. (:pr:`1119`)
- The ``expect_error`` argument to :func:`cocotb.test` now accepts a specific exception type. (:pr:`1116`)
- New environment variable :envvar:`COCOTB_RESULTS_FILE`, to allow configuration of the xunit XML output filename.  (:pr:`1053`)
- A new ``bus_separator`` argument to :class:`cocotb.drivers.BusDriver`. (:pr:`1160`)
- A new ``start_high`` argument to :meth:`cocotb.clock.Clock.start`. (:pr:`1036`)
- A new :data:`cocotb.__version__` constant, which contains the version number of the running cocotb. (:pr:`1196`)

Notable changes and bug fixes
-----------------------------

- ``DeprecationWarning``\ s are now shown in the output by default.
- Tracebacks are now preserved correctly for exceptions in Python 2.
  The tracebacks in all Python versions are now a little shorter.
- :func:`cocotb.external` and :func:`cocotb.function` now work more reliably and with fewer race conditions.
- A failing ``assert`` will be considered a test failure. Previously, it was considered a test *error*.
- :meth:`~cocotb.handle.NonConstantObject.drivers` and :meth:`~cocotb.handle.NonConstantObject.loads` now also work correctly in Python 3.7 onwards.
- :class:`cocotb.triggers.Timer` can now be used with :class:`decimal.Decimal` instances, allowing constructs like ``Timer(Decimal('1e-9'), units='sec')`` as an alternate spelling for ``Timer(100, units='us')``. (:pr:`1114`)
- Many (editorial) documentation improvements.

Deprecations
------------

- ``cocotb.result.raise_error`` and ``cocotb.result.create_error`` are deprecated in favor of using Python exceptions directly.
  :class:`~cocotb.result.TestError` can still be used if the same exception type is desired. (:pr:`1109`)
- The ``AvalonSTPktsWithChannel`` type is deprecated.
  Use the ``report_channel`` argument to :class:`~cocotb.monitors.avalon.AvalonSTPkts` instead.
- The ``colour`` attribute of log objects like ``cocotb.log`` or ``some_coro.log`` is deprecated.
  Use :func:`cocotb.utils.want_color_output` instead. (:pr:`1231`)

Other news
----------

- cocotb is now packaged for Fedora Linux and available as `python-cocotb <https://apps.fedoraproject.org/packages/python-cocotb>`_. (`Fedora bug #1747574 <https://bugzilla.redhat.com/show_bug.cgi?id=1747574>`_) (thanks Ben Rosser)

cocotb 1.2.0
============

Released on 24 July 2019

New features
------------

- cocotb is now built as Python package and installable through pip. (:pr:`517`, :pr:`799`, :pr:`800`, :pr:`803`, :pr:`805`)
- Support for ``async`` functions and generators was added (Python 3 only). Please have a look at :ref:`async_functions` for an example how to use this new feature.
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

Deprecations
------------

- The `bits` argument to :class:`~cocotb.binary.BinaryValue`, which is now called `n_bits`.
- The `logger` attribute of log objects like ``cocotb.log`` or ``some_coro.log``, which is now just an alias for ``self``.
- The ``cocotb.utils.get_python_integer_types`` function, which was intended to be private.

Known issues
------------

- Depending on your simulation, cocotb 1.2 might be roughly 20 percent slower than cocotb 1.1.
  Much of the work in this release cycle went into fixing correctness bugs in the scheduler, sometimes at the cost of performance.
  We are continuing to investigate this in issue :issue:`961`.
  Independent of the cocotb version, we recommend using the latest Python 3 version, which is shown to be significantly faster than previous Python 3 versions, and slightly faster than Python 2.7.

Please have a look at the `issue tracker <https://github.com/cocotb/cocotb/issues>`_ for more outstanding issues and contribution opportunities.

cocotb 1.1
==========

Released on 24 January 2019.

This release is the result of four years of work with too many bug fixes, improvements and refactorings to name them all.
Please have a look at the release announcement `on the mailing list <https://lists.librecores.org/pipermail/cocotb/2019-January/000053.html>`_ for further information.

cocotb 1.0
==========

Released on 15 February 2015.

New features
------------

- FLI support for ModelSim
- Mixed Language, Verilog and VHDL
- Windows
- 300% performance improvement with VHPI interface
- WaveDrom support for wave diagrams.


cocotb 0.4
==========

Released on 25 February 2014.


New features
------------

- Issue :issue:`101`: Implement Lock primitive to support mutex
- Issue :issue:`105`: Compatibility with Aldec Riviera-Pro
- Issue :issue:`109`: Combine multiple :file:`results.xml` into a single results file
- Issue :issue:`111`: XGMII drivers and monitors added
- Issue :issue:`113`: Add operators to ``BinaryValue`` class
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

Released on 27 September 2013.

This contains a raft of fixes and feature enhancements.


cocotb 0.2
==========

Released on 19 July 2013.

New features
------------

- Release 0.2 supports more simulators and increases robustness over 0.1.
- A centralized installation is now supported (see documentation) with supporting libraries build when the simulation is run for the first time.


cocotb 0.1
==========

Released on 9 July 2013.

- The first release of cocotb.
- Allows installation and running against Icarus, VCS, Aldec simulators.
