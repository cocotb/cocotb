.. _simulator-support:

*****************
Simulator Support
*****************

This page lists the simulators that cocotb can be used with
and documents specifics, limitations, workarounds etc.

In general, cocotb can be used with any simulator supporting the industry-standard VPI, VHPI or FLI interfaces.
However, in practice simulators exhibit small differences in behavior that cocotb mostly takes care of.

If a simulator you would like to use with cocotb is not listed on this page
open an issue at the `cocotb GitHub issue tracker <https://github.com/cocotb/cocotb/issues>`_.


.. _sim-icarus:

Icarus Verilog
==============

In order to use this simulator, set :make:var:`SIM` to ``icarus``:

.. code-block:: bash

    make SIM=icarus

.. note::

    A working installation of `Icarus Verilog <https://github.com/steveicarus/iverilog>`_ is required.
    You can find installation instructions `in the Icarus Verilog Installation Guide <https://iverilog.fandom.com/wiki/Installation_Guide>`_.

.. _sim-icarus-waveforms:

Waveforms
---------

Icarus Verilog can produce waveform traces in the FST format.
FST traces are much smaller and more efficient to write than VCD.
They can be viewed with GTKWave or with `Surfer <https://surfer-project.org/>`_.

To enable FST tracing, set :make:var:`WAVES` to ``1``.

.. code-block:: bash

    make SIM=icarus WAVES=1

By default, the wave file will be named `<hdl_toplevel>.fst`. Unlike other simulators, it will be placed in the build directory, rather than the test directory.

To redirect the wave file to a different location, use the plusarg `dumpfile_path` when running the test.

.. _sim-icarus-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:icarus <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Aicarus>`_


.. _sim-verilator:

Verilator
=========

.. warning::

    **cocotb supports Verilator 5.036+.**

In order to use this simulator, set :make:var:`SIM` to ``verilator``:

.. code-block:: bash

    make SIM=verilator

.. note::

    A working installation of `Verilator <https://www.veripool.org/verilator/>`_ is required.
    You can find installation instructions `in the Verilator documentation <https://verilator.org/guide/latest/install.html>`_.

.. versionadded:: 1.3

.. versionchanged:: 1.5 Improved cocotb support and greatly improved performance when using a higher time precision.

.. versionchanged:: 2.0

    Reimplemented the Verilator evaluator loop used in cocotb tests.
    This allowed for better performance and behavior more consistent with event-based simulators.
    Additionally, added support for inertial writes,
    which noticeably improves performance.

Coverage
--------

To enable :term:`HDL` code coverage, add Verilator's coverage option(s) to the :make:var:`EXTRA_ARGS` make variable, for example:

 .. code-block:: make

    EXTRA_ARGS += --coverage

This will result in coverage data being written to :file:`coverage.dat`.

.. _sim-verilator-waveforms:

Waveforms
---------

To get waveforms in VCD format, add Verilator's trace option(s) to the
:make:var:`EXTRA_ARGS` make variable, for example in a Makefile:

  .. code-block:: make

    EXTRA_ARGS += --trace --trace-structs

To set the same options on the command line, use ``EXTRA_ARGS="--trace --trace-structs" make ...``.
A VCD file named ``dump.vcd`` will be generated in the current directory.

Verilator can produce waveform traces in the FST format.
FST traces are much smaller and more efficient to write.
They can be viewed with GTKWave or with `Surfer <https://surfer-project.org/>`_.

To enable FST tracing, add ``--trace-fst`` to :make:var:`EXTRA_ARGS` as shown below.

  .. code-block:: make

    EXTRA_ARGS += --trace --trace-fst --trace-structs

The resulting file will be :file:`dump.fst` and can be opened by ``gtkwave dump.fst``.

.. _sim-verilator-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:verilator <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Averilator>`_


.. _sim-vcs:

Synopsys VCS
============

In order to use this simulator, set :make:var:`SIM` to ``vcs``:

.. code-block:: bash

    make SIM=vcs

cocotb currently only supports :term:`VPI` for Synopsys VCS, not :term:`VHPI`.

.. _sim-vcs-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:vcs <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Avcs>`_


.. _sim-aldec:
.. _sim-riviera:

Aldec Riviera-PRO
=================

In order to use this simulator, set :make:var:`SIM` to ``riviera``:

.. code-block:: bash

    make SIM=riviera

.. note::

   On Windows, do not install the C++ compiler, i.e. unselect it during the installation process of Riviera-PRO.
   (A workaround is to remove or rename the ``mingw`` directory located in the Riviera-PRO installation directory.)

.. deprecated:: 1.4

   Support for Riviera-PRO was previously available with ``SIM=aldec``.

The :envvar:`LICENSE_QUEUE` environment variable can be used for this simulator –
this setting will be mirrored in the TCL ``license_queue`` variable to control runtime license checkouts.


.. _sim-aldec-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:riviera <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Ariviera>`_


.. _sim-activehdl:

Aldec Active-HDL
================

In order to use this simulator, set :make:var:`SIM` to ``activehdl``:

.. code-block:: bash

    make SIM=activehdl

.. warning::

    cocotb does not work with some versions of Active-HDL (see :issue:`1494`).

    Known affected versions:

    - Aldec Active-HDL 10.4a
    - Aldec Active-HDL 10.5a

.. _sim-activehdl-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:activehdl <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Aactivehdl>`_


.. _sim-questa:

Mentor/Siemens EDA Questa
=========================

In order to use this simulator, set :make:var:`SIM` to ``questa``:

.. code-block:: bash

    make SIM=questa

Cocotb implements two flows for Questa.
The most suitable flow is chosen based on the Questa version being used.

The newer **QIS/Qrun flow** uses the Questa Information System (QIS) together with the ``qrun`` command.
One of the most visible user-facing benefits of the ``qrun`` flow is the ability to automatically order VHDL sources.
The use of the QIS should reduce the overhead from accessing design internals at runtime and mandates the use of Visualizer as GUI.

The QIS/qrun flow is chosen automatically if Questa 2025.2 or newer is detected.
Users can explicitly use the QIS/Qrun flow with :make:var:`SIM=questa-qisqrun <SIM>`.
If you are passing simulator-specific arguments to the Makefile, we recommend not relying on the automatic flow selection and instead explicitly selecting a flow by using either ``SIM=questa-qisqrun`` or ``SIM=questa-compat`` to ensure they are interpreted as expected.

The **compat flow** uses the commands ``vlog``, ``vopt`` and ``vsim`` to build and run the simulation, together with the ``+acc`` switch to enable design access for cocotb.

The compat flow is used for ModelSim and Questa older than 2025.2.
Users can explicitly use the compat flow with ``SIM=questa-compat``.

In order to start Questa with the graphical interface and for the simulator to remain active after the tests have completed, set :make:var:`GUI=1`.

Users of the QIS/Qrun flow can set ``GUI=livesim`` to open Visualizer during the simulation in Live Simulation mode (an alias for ``GUI=1``), or set ``GUI=postsim`` to open Visualizer after the simulation has ended (Post Simulation mode).

Starting with Questa 2022.3 and cocotb 1.7 users with VHDL toplevels can choose between two communication interfaces between Questa and cocotb: the proprietary FLI and VHPI.
For backwards-compatibility cocotb defaults to FLI.
Users can choose VHPI instead by setting the :envvar:`VHDL_GPI_INTERFACE` environment variable to ``vhpi`` before running cocotb.

For more information, see :ref:`sim-modelsim`.

.. _sim-questa-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:questa <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Aquesta>`_


.. _sim-modelsim:

Mentor/Siemens EDA ModelSim
===========================

In order to use this simulator, set :make:var:`SIM` to ``modelsim``:

.. code-block:: bash

    make SIM=modelsim

Any ModelSim PE or ModelSim PE derivatives (like the ModelSim Microsemi, Intel, Lattice Editions) do not support the VHDL :term:`FLI` feature.
If you try to use them with :term:`FLI`, you will see a ``vsim-FLI-3155`` error:

.. code-block:: bash

    ** Error (suppressible): (vsim-FLI-3155) The FLI is not enabled in this version of ModelSim.

ModelSim DE and SE (and Questa, of course) support the :term:`FLI`.

In order to start ModelSim with the graphical interface and for the simulator to remain active after the tests have completed, set :make:var:`GUI=1 <GUI>`.

If you have previously launched a test without this setting, you might have to delete the :make:var:`SIM_BUILD` directory (``sim_build`` by default) to get the correct behavior.

.. _sim-modelsim-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:modelsim <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Amodelsim>`_


.. _sim-incisive:

Cadence Incisive
================

In order to use this simulator, set :make:var:`SIM` to ``ius``:

.. code-block:: bash

    make SIM=ius

For more information, see :ref:`sim-xcelium`.

.. _sim-incisive-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:ius <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Aius>`_


.. _sim-xcelium:

Cadence Xcelium
===============

In order to use this simulator, set :make:var:`SIM` to ``xcelium``:

.. code-block:: bash

    make SIM=xcelium

The simulator automatically loads :term:`VPI` even when only :term:`VHPI` is requested.

Testing designs with VHDL toplevels is only supported with Xcelium 23.09.004 and newer.

.. _sim-xcelium-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:xcelium <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Axcelium>`_


.. _sim-ghdl:

GHDL
====

.. warning::

    GHDL support in cocotb is experimental.
    Some features of cocotb may not work correctly or at all.
    At least GHDL 2.0 is required.

In order to use this simulator, set :make:var:`SIM` to ``ghdl``:

.. code-block:: bash

    make SIM=ghdl

.. note::

    A working installation of `GHDL <https://ghdl.github.io/ghdl/about.html>`_ is required.
    You can find installation instructions `in the GHDL documentation <https://ghdl.github.io/ghdl/getting.html>`_.

Noteworthy is that despite GHDL being a VHDL simulator, it implements the :term:`VPI` interface.
This prevents cocotb from accessing some VHDL-specific constructs, like 9-value signals.

To specify a VHDL architecture to simulate, set the ``ARCH`` make variable to the architecture name.

.. _sim-ghdl-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:ghdl <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Aghdl>`_


.. _sim-ghdl-waveforms:

Waveforms
---------

To get waveforms in VCD format, set the :make:var:`SIM_ARGS` option to ``--vcd=anyname.vcd``,
for example in a Makefile:

.. code-block:: make

    SIM_ARGS+=--vcd=anyname.vcd

The option can be set on the command line, as shown in the following example.

.. code-block:: bash

    SIM_ARGS=--vcd=anyname.vcd make SIM=ghdl

A VCD file named :file:`anyname.vcd` will be generated in the current directory.

:make:var:`SIM_ARGS` can also be used to pass command line arguments related to :ref:`other waveform formats supported by GHDL <ghdl:export_waves>`.


.. _sim-nvc:

NVC
===

.. note::

    NVC version **1.11.0** or later is required.

.. note::

    Using NVC versions greater than **1.16.0** will automatically add the ``--preserve-case`` option build commands.
    This is standards-compliant behavior and may become default behavior in NVC, so think twice before overriding it.

In order to use this simulator, set :make:var:`SIM` to ``nvc``:

.. code-block:: bash

    make SIM=nvc

.. _sim-nvc-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:nvc <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Anvc>`_

Coverage
--------

To enable code coverage, add ``--cover`` to :make:var:`SIM_ARGS`, for example
in a Makefile:

.. code-block:: make

    SIM_ARGS += --cover

Specifying types of coverage is also supported.
For example, to collect statement and branch coverage:

.. code-block:: make

    SIM_ARGS += --cover=statement,branch

The ``covdb`` files will be placed in the :make:var:`RTL_LIBRARY` subdirectory of :make:var:`SIM_BUILD`.
For instructions on how to specify coverage types and produce a report, refer to `NVC's code coverage documentation <https://www.nickg.me.uk/nvc/manual.html#CODE_COVERAGE>`_.

.. _sim-nvc-waveforms:

Waveforms
---------

To get waveforms in FST format, set the :make:var:`SIM_ARGS` option to ``--wave=anyname.fst``, for example in a Makefile:

.. code-block:: make

    SIM_ARGS += --wave=anyname.fst

:make:var:`SIM_ARGS` can also be used to set the waveform output to VCD by adding ``--format=vcd``.


.. _sim-cvc:

Tachyon DA CVC
==============

In order to use `Tachyon DA <http://www.tachyon-da.com/>`_'s `CVC <https://github.com/cambridgehackers/open-src-cvc>`_ simulator,
set :make:var:`SIM` to ``cvc``:

.. code-block:: bash

    make SIM=cvc

Note that cocotb's makefile is using CVC's interpreted mode.

.. _sim-cvc-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:cvc <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Acvc>`_

.. _sim-dsim:

Siemens DSim
============

.. warning::

    DSim support for cocotb is experimental.
    Some features of cocotb may not work correctly or at all.
    At least DSim version 2025 is required.

In order to use this simulator, set :make:var:`SIM` to ``dsim``:

.. code-block:: bash

    make SIM=dsim

.. note::

    A working installation of `DSim <https://altair.com/dsim>`_ is required.
    You can install DSim simulator directly from `Altair Marketplace <https://altairone.com/Marketplace?tab=Info&app=dsim>`_ and find information regarding getting a free license.

.. _sim-dsim-waveforms:

Waveforms
---------

DSim can produce waveform traces in the VCD format.
They can be viewed with GTKWave or with `Surfer <https://surfer-project.org/>`_.

To enable VCD tracing, set :make:var:`WAVES` to ``1``.

.. code-block:: bash

    make SIM=dsim WAVES=1

.. _sim-dsim-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:dsim <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Adsim>`_

.. versionadded:: 2.0
