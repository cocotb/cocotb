*************
Release Notes
*************

.. spelling::
   dev

All releases are available from the `GitHub Releases Page <https://github.com/cocotb/cocotb/releases>`_.

.. include:: master-notes.rst

.. towncrier release notes start

Cocotb 1.5.0rc1 (2021-02-23)
============================

Features
--------

- Support for building with Microsoft Visual C++ has been added.
  See :ref:`install` for more details. (:pr:`1798`)
- Makefiles now automatically deduce :make:var:`TOPLEVEL_LANG` based on the value of :make:var:`VERILOG_SOURCES` and :make:var:`VHDL_SOURCES`.
  Makefiles also detect incorrect usage of :make:var:`TOPLEVEL_LANG` for simulators that only support one language. (:pr:`1982`)
- :meth:`cocotb.fork` will now raise a descriptive :class:`TypeError` if a coroutine function is passed into them. (:pr:`2006`)
- Added :meth:`cocotb.scheduler.start_soon <cocotb.scheduler.Scheduler.start_soon>` which schedules a coroutine to start *after* the current coroutine yields control.
  This behavior is distinct from :func:`cocotb.fork` which schedules the given coroutine immediately. (:pr:`2023`)
- If ``pytest`` is installed, its assertion-rewriting framework will be used to
  produce more informative tracebacks from the :keyword:`assert` statement. (:pr:`2028`)
- The handle to :envvar:`TOPLEVEL`, typically seen as the first argument to a cocotb test function, is now available globally as :data:`cocotb.top`. (:pr:`2134`)
- The ``units`` argument to :class:`cocotb.triggers.Timer`,
  :class:`cocotb.clock.Clock` and :func:`cocotb.utils.get_sim_steps`,
  and the ``timeout_unit`` argument to
  :func:`cocotb.triggers.with_timeout` and :class:`cocotb.test`
  now accepts ``'step'`` to mean the simulator time step.
  This used to be expressed using ``None``, which is now deprecated. (:pr:`2171`)
- :func:`cocotb.regression.TestFactory.add_option` now supports groups of options when a full Cartesian product is not desired (:pr:`2175`)
- Added asyncio-style queues, :class:`cocotb.queue.Queue`, :class:`cocotb.queue.PriorityQueue`, and :class:`cocotb.queue.LifoQueue`. (:pr:`2297`)
- Support for the SystemVerilog type ``bit`` has been added. (:pr:`2322`)
- Added the ``--lib-dir``,  ``--lib-name`` and ``--lib-name-path`` options to the ``cocotb-config`` command to make cocotb integration into existing flows easier. (:pr:`2387`)
- Support for using Questa's VHPI has been added.
  Use :make:var:`VHDL_GPI_INTERFACE` to select between using the FLI or VHPI when dealing with VHDL simulations.
  Note that VHPI support in Questa is still experimental at this time. (:pr:`2408`)


Bugfixes
--------

- Assigning Python integers to signals greater than 32 bits wide will now work correctly for negative values. (:pr:`913`)
- Fix GHDL's library search path, allowing libraries other than *work* to be used in simulation. (:pr:`2038`)
- Tests skipped by default (created with `skip=True`) can again be run manually by setting the :envvar:`TESTCASE` variable. (:pr:`2045`)
- In :ref:`Icarus Verilog <sim-icarus>`, generate blocks are now accessible directly via lookup without having to iterate over parent handle. (:pr:`2079`, :pr:`2143`)

    .. code-block:: python3

        # Example pseudo-region
        dut.genblk1       #<class 'cocotb.handle.HierarchyArrayObject'>

    .. consume the towncrier issue number on this line. (:pr:`2079`)
- Fixed an issue with VHPI on Mac OS and Linux where negative integers were returned as large positive values. (:pr:`2129`)


Improved Documentation
----------------------

- The  :ref:`mixed_signal` example has been added,
  showing how to use HDL helper modules in cocotb testbenches that exercise
  two mixed-signal (i.e. analog and digital) designs. (:pr:`1051`)
- New example :ref:`matrix_multiplier`. (:pr:`1502`)
- A :ref:`refcard` showing the most used features of cocotb has been added. (:pr:`2321`)
- A chapter :ref:`custom-flows` has been added. (:pr:`2340`)


Deprecations and Removals
-------------------------

- The contents of :mod:`cocotb.generators` have been deprecated. (:pr:`2047`)
- The outdated "Sorter" example has been removed from the documentation. (:pr:`2049`)
- Passing :class:`bool` values to ``expect_error`` option of :class:`cocotb.test` is deprecated.
  Pass a specific :class:`Exception` or a tuple of Exceptions instead. (:pr:`2117`)
- The system task overloads for ``$info``, ``$warn``, ``$error`` and ``$fatal`` in Verilog and mixed language testbenches have been removed. (:pr:`2133`)
- :class:`~cocotb.result.TestError` has been deprecated, use :ref:`python:bltin-exceptions`. (:pr:`2177`)
- The undocumented class ``cocotb.xunit_reporter.File`` has been removed. (:pr:`2200`)
- Deprecated :class:`cocotb.hook` and :envvar:`COCOTB_HOOKS`.
  See the documentation for :class:`cocotb.hook` for suggestions on alternatives. (:pr:`2201`)
- Deprecate :func:`~cocotb.utils.pack` and :func:`~cocotb.utils.unpack` and the use of :class:`python:ctypes.Structure` in signal assignments. (:pr:`2203`)
- The outdated "ping" example has been removed from the documentation and repository. (:pr:`2232`)
- The access modes of many interfaces in the cocotb core libraries were re-evaluated.
  Some interfaces that were previously public are now private and vice versa.
  Accessing the methods through their old name will create a :class:`DeprecationWarning`.
  In the future, the deprecated names will be removed. (:pr:`2278`)
- The bus and testbenching components in cocotb have been officially moved to the `cocotb-bus <https://github.com/cocotb/cocotb-bus>`_ package.
  This includes
  :class:`~cocotb_bus.bus.Bus`,
  :class:`~cocotb_bus.scoreboard.Scoreboard`,
  everything in :mod:`cocotb_bus.drivers <cocotb.drivers>`,
  and everything in :mod:`cocotb_bus.monitors <cocotb.monitors>`.
  Documentation will remain in the main cocotb repository for now.
  Old names will continue to exist, but their use will cause a :class:`DeprecationWarning`,
  and will be removed in the future. (:pr:`2289`)


Changes
-------

- Assigning out-of-range Python integers to signals would previously truncate the value silently for signal widths <= 32 bits and truncate the value with a warning for signal widths > 32 bits.
  Assigning out-of-range Python integers to signals will now raise an :exc:`OverflowError`. (:pr:`913`)
- Updated :class:`~cocotb_bus.drivers.Driver`, :class:`~cocotb_bus.monitors.Monitor`, and all their subclasses to use the :keyword:`async`/:keyword:`await` syntax instead of the :keyword:`yield` syntax. (:pr:`2022`)
- The package build process is now fully :pep:`517` compliant. (:pr:`2091`)
- Improved support and performance for :ref:`sim-verilator` (version 4.106 or later now required). (:pr:`2105`)
- Changed how libraries are specified in :envvar:`GPI_EXTRA` to allow specifying libraries with paths, and names that don't start with "lib". (:pr:`2341`)


Cocotb 1.4.0 (2020-07-08)
=========================

Features
--------

- :class:`~cocotb.triggers.Lock` can now be used in :keyword:`async with` statements. (:pr:`1031`)
- Add support for distinguishing between ``net`` (``vpiNet``) and ``reg`` (``vpiReg``) type when using the VPI interface. (:pr:`1107`)
- Support for dropping into :mod:`pdb` upon failure, via the new :envvar:`COCOTB_PDB_ON_EXCEPTION` environment variable (:pr:`1180`)
- Simulators run through a Tcl script (Aldec Riviera Pro and Mentor simulators) now support a new :make:var:`RUN_ARGS` Makefile variable, which is passed to the first invocation of the tool during runtime. (:pr:`1244`)
- Cocotb now supports the following example of forking a *non-decorated* :ref:`async coroutine <async_functions>`.

  .. code-block:: python3

     async def example():
         for i in range(10):
             await cocotb.triggers.Timer(10, "ns")

     cocotb.fork(example())

  ..
     towncrier will append the issue number taken from the file name here:

  Issue (:pr:`1255`)
- The cocotb log configuration is now less intrusive, and only configures the root logger instance, ``logging.getLogger()``, as part of :func:`cocotb.log.default_config` (:pr:`1266`).

  As such, it is now possible to override the default cocotb logging behavior with something like::

      # remove the cocotb log handler and formatting
      root = logging.getLogger()
      for h in root.handlers[:]:
          root.remove_handler(h)
          h.close()

      # add your own
      logging.basicConfig()

  .. consume the towncrier issue number on this line. (:pr:`1266`)
- Support for ``vpiRealNet`` (:pr:`1282`)
- The colored output can now be disabled by the :envvar:`NO_COLOR` environment variable. (:pr:`1309`)
- Cocotb now supports deposit/force/release/freeze actions on simulator handles, exposing functionality similar to the respective Verilog/VHDL assignments.

  .. code-block:: python3

     from cocotb.handle import Deposit, Force, Release, Freeze

     dut.q <= 1            # A regular value deposit
     dut.q <= Deposit(1)   # The same, higher verbosity
     dut.q <= Force(1)     # Force value of q to 1
     dut.q <= Release()    # Release q from a Force
     dut.q <= Freeze()     # Freeze the current value of q

  ..
     towncrier will append the issue number taken from the file name here:

  Issue (:pr:`1403`)
- Custom logging handlers can now access the simulator time using
  :attr:`logging.LogRecord.created_sim_time`, provided the
  :class:`~cocotb.log.SimTimeContextFilter` filter added by
  :func:`~cocotb.log.default_config` is not removed from the logger instance. (:pr:`1411`)
- Questa now supports :envvar:`PLUSARGS`.
  This requires that ``tcl.h`` be present on the system.
  This is likely included in your installation of Questa, otherwise, specify ``CFLAGS=-I/path/to/tcl/includedir``. (:pr:`1424`)
- The name of the entry point symbol for libraries in :envvar:`GPI_EXTRA` can now be customized.
  The delimiter between each library in the list has changed from ``:`` to ``,``. (:pr:`1457`)
- New methods for setting the value of a :class:`~cocotb.handle.NonHierarchyIndexableObject` (HDL arrays). (:pr:`1507`)

  .. code-block:: python3

      # Now supported
      dut.some_array <= [0xAA, 0xBB, 0xCC]
      dut.some_array.value = [0xAA, 0xBB, 0xCC]

      # For simulators that support n-dimensional arrays
      dut.some_2d_array <= [[0xAA, 0xBB], [0xCC, 0xDD]]
      dut.some_2d_array.value = [[0xAA, 0xBB], [0xCC, 0xDD]]

  .. consume the towncrier issue number on this line. (:pr:`1507`)
- Added support for Aldec's Active-HDL simulator. (:pr:`1601`)
- Including ``Makefile.inc`` from user makefiles is now a no-op and deprecated. Lines like  ``include $(shell cocotb-config --makefiles)/Makefile.inc`` can be removed from user makefiles without loss in functionality. (:pr:`1629`)
- Support for using ``await`` inside an embedded IPython terminal, using :mod:`cocotb.ipython_support`. (:pr:`1649`)
- Added :meth:`~cocotb.triggers.Event.is_set`, so users may check if an :class:`~cocotb.triggers.Event` has fired. (:pr:`1723`)
- The :func:`cocotb.simulator.is_running` function was added so a user of cocotb could determine if they are running within a simulator. (:pr:`1843`)


Bugfixes
--------

- Tests which fail at initialization, for instance due to no ``yield`` being present, are no longer silently ignored (:pr:`1253`)
- Tests that were not run because predecessors threw :class:`cocotb.result.SimFailure`, and caused the simulator to exit, are now recorded with an outcome of :class:`cocotb.result.SimFailure`.
  Previously, these tests were ignored. (:pr:`1279`)
- Makefiles now correctly fail if the simulation crashes before a ``results.xml`` file can be written. (:pr:`1314`)
- Logging of non-string messages with colored log output is now working. (:pr:`1410`)
- Getting and setting the value of a :class:`~cocotb.handle.NonHierarchyIndexableObject` now iterates through the correct range of the simulation object, so arrays that do not start/end at index 0 are supported. (:pr:`1507`)
- The :class:`~cocotb.monitors.xgmii.XGMII` monitor no longer crashes on Python 3, and now assembles packets as :class:`bytes` instead of :class:`str`. The :class:`~cocotb.drivers.xgmii.XGMII` driver has expected :class:`bytes` since cocotb 1.2.0. (:pr:`1545`)
- ``signal <= value_of_wrong_type`` no longer breaks the scheduler, and throws an error immediately. (:pr:`1661`)
- Scheduling behavior is now consistent before and after the first :keyword:`await` of a :class:`~cocotb.triggers.GPITrigger`. (:pr:`1705`)
- Iterating over ``for generate`` statements using VHPI has been fixed. This bug caused some simulators to crash, and was a regression in version 1.3. (:pr:`1882`)
- The :class:`~cocotb.drivers.xgmii.XGMII` driver no longer emits a corrupted word on the first transfer. (:pr:`1905`)


Improved Documentation
----------------------

- If a makefile uses cocotb's :file:`Makefile.sim`, ``make help`` now lists the supported targets and variables. (:pr:`1318`)
- A new section :ref:`rotating-logger` has been added. (:pr:`1400`)
- The documentation at http://docs.cocotb.org/ has been restructured,
  making it easier to find relevant information. (:pr:`1482`)


Deprecations and Removals
-------------------------

- :func:`cocotb.utils.reject_remaining_kwargs` is deprecated, as it is no longer
  needed now that we only support Python 3.5 and newer. (:pr:`1339`)
- The value of :class:`cocotb.handle.StringObject`\ s is now of type :class:`bytes`, instead of  :class:`str` with an implied ASCII encoding scheme. (:pr:`1381`)
- :class:`ReturnValue` is now deprecated. Use a :keyword:`return` statement instead; this works in all supported versions of Python. (:pr:`1489`)
- The makefile variable :make:var:`VERILATOR_TRACE`
  that was not supported for all simulators has been deprecated.
  Using it prints a deprecation warning and points to the documentation section
  :ref:`simulator-support` explaining how to get the same effect by other means. (:pr:`1495`)
- ``BinaryValue.get_hex_buff`` produced nonsense and has been removed. (:pr:`1511`)
- Passing :class:`str` instances to :func:`cocotb.utils.hexdump` and :func:`cocotb.utils.hexdiffs` is deprecated. :class:`bytes` objects should be passed instead. (:pr:`1519`)
- ``Makefile.pylib``, which provided helpers for building C extension modules for Python, has been removed.
  Users of the ``PYTHON_LIBDIR`` and ``PYTHON_INCLUDEDIR`` variables will now have to compute these values themselves.
  See the ``endian_swapper`` example for how to do this. (:pr:`1632`)
- Makefile and documentation for the NVC simulator which has never worked have been removed. (:pr:`1693`)


Changes
-------

- Cocotb no longer supports Python 2, at least Python 3.5 is now required.
  Users of Python 2.7 can still use cocotb 1.3, but are heavily encouraged to update.
  It is recommended to use the latest release of Python 3 for improved performance over older Python 3 versions. (:pr:`767`)
- Mentor Questa, Aldec Riviera-PRO and GHDL are now started in the directory containing the Makefile and also save :file:`results.xml` there, bringing them in line with the behavior used by other simulators. (:pr:`1598`) (:pr:`1599`) (:pr:`1063`)
- Tests are now evaluated in order of their appearance in the :envvar:`MODULE` environment variable, their stage, and the order of invocation of the :class:`cocotb.test` decorator within a module. (:pr:`1380`)
- All libraries are compiled during installation to the ``cocotb/libs`` directory.
  The interface libraries ``libcocotbvpi`` and ``libcocotbvhpi`` have been renamed to have a ``_simulator_name`` postfix.
  The ``simulator`` module has moved to :mod:`cocotb.simulator`.
  The ``LD_LIBRARY_PATH`` environment variable no longer needs to be set by the makefiles, as the libraries now discover each other via ``RPATH`` settings. (:pr:`1425`)
- Cocotb must now be :ref:`installed <installation-via-pip>` before it can be used. (:pr:`1445`)
- :attr:`cocotb.handle.NonHierarchyIndexableObject.value` is now a list in left-to-right range order of the underlying simulation object.
  Previously the list was always ordered low-to-high. (:pr:`1507`)
- Various binary representations have changed type from :class:`str` to :class:`bytes`. These include:

  * :attr:`cocotb.binary.BinaryValue.buff`, which as a consequence means :meth:`cocotb.binary.BinaryValue.assign` no longer accepts malformed ``10xz``-style :class:`str`\ s (which were treated as binary).
  * The objects produced by :mod:`cocotb.generators.byte`, which means that single bytes are represented by :class:`int` instead of 1-character :class:`str`\ s.
  * The packets produced by the :class:`~cocotb.drivers.avalon.AvalonSTPkts`.

  Code working with these objects may find it needs to switch from creating :class:`str` objects like ``"this"`` to :class:`bytes` objects like ``b"this"``.
  This change is a consequence of the move to Python 3. (:pr:`1514`)
- There's no longer any need to set the ``PYTHON_BIN`` makefile variable, the Python executable automatically matches the one cocotb was installed into. (:pr:`1574`)
- The :make:var:`SIM` setting for Aldec Riviera-PRO has changed from ``aldec`` to ``riviera``. (:pr:`1691`)
- Certain methods on the :mod:`cocotb.simulator` Python module now throw a :exc:`RuntimeError` when no simulator is present, making it safe to use :mod:`cocotb` without a simulator present. (:pr:`1843`)
- Invalid values of the environment variable :envvar:`COCOTB_LOG_LEVEL` are no longer ignored.
  They now raise an exception with instructions how to fix the problem. (:pr:`1898`)


cocotb 1.3.2
============

Released on 08 July 2020

Notable changes and bug fixes
-----------------------------

- Iterating over ``for generate`` statements using VHPI has been fixed.
  This bug caused some simulators to crash, and was a regression in version 1.3.1. (:pr:`1882`)

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
- New environment variable :envvar:`COCOTB_RESULTS_FILE`, to allow configuration of the xUnit XML output filename.  (:pr:`1053`)
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
