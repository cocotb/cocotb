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

.. _sim-icarus-accessing-bits:

Accessing bits in a vector
--------------------------

Accessing bits of a vector directly was not possible until (including) version 10.3:

.. code-block:: python3

    dut.stream_in_data[2].value = 1

See also https://github.com/steveicarus/iverilog/issues/323.

.. _sim-icarus-waveforms:

Waveforms
---------

To get waveforms in VCD format some Verilog code must be added
to the top component as shown in the example below:

.. code-block:: verilog

    module button_deb(
        input  clk,
        input  rst,
        input  button_in,
        output button_valid);

    //... Verilog module code here

    // the "macro" to dump signals
    `ifdef COCOTB_SIM
    initial begin
      $dumpfile ("button_deb.vcd");
      $dumpvars (0, button_deb);
      #1;
    end
    `endif
    endmodule

.. _sim-icarus-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:icarus <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Aicarus>`_


.. _sim-verilator:

Verilator
=========

.. warning::

    Verilator is in the process of adding more functionality to its VPI interface, which is used by cocotb to access the design.
    Therefore, Verilator support in cocotb is currently experimental.
    Some features of cocotb may not work correctly or at all.

    **Currently cocotb only supports Verilator 4.106 (no earlier or later version).**
    See also the corresponding cocotb issue :issue:`2300` and `upstream issue <https://github.com/verilator/verilator/issues/2778>`_.

In order to use this simulator, set :make:var:`SIM` to ``verilator``:

.. code-block:: bash

    make SIM=verilator

One major limitation compared to standard Verilog simulators is that it does not support delayed assignments when accessed from cocotb.

To run cocotb with Verilator, you need ``verilator`` in your PATH.

.. versionadded:: 1.3

.. versionchanged:: 1.5 Improved cocotb support and greatly improved performance when using a higher time precision.

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

Verilator can produce waveform traces in the FST format, the native format of GTKWave.
FST traces are much smaller and more efficient to write, but require the use of GTKWave.

To enable FST tracing, add ``--trace-fst`` to :make:var:`EXTRA_ARGS` as shown below.

  .. code-block:: make

    EXTRA_ARGS += --trace-fst --trace-structs

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

For more information, see :ref:`sim-modelsim`.

.. _sim-questa-issues:

Issues for this simulator
-------------------------

* `All issues with label category:simulators:questa <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Acategory%3Asimulators%3Aquesta>`_
* Questa 2021.1 and later added experimental support the VHPI interface in addition to the proprietary FLI interface.
  However, this support is not complete yet and users of cocotb should continue to use FLI for the time being.

.. _sim-modelsim:

Mentor/Siemens EDA ModelSim
===========================

In order to use this simulator, set :make:var:`SIM` to ``modelsim``:

.. code-block:: bash

    make SIM=modelsim

.. note::

   In order to use :term:`FLI` (for VHDL), a ``vdbg`` executable from the simulator installation directory needs to be available on the ``PATH`` during cocotb installation.
   This is needed to access the proprietary :file:`mti.h` header file.

Any ModelSim PE or ModelSim PE derivatives (like the ModelSim Microsemi, Intel, Lattice Editions) do not support the VHDL :term:`FLI` feature.
If you try to use them with :term:`FLI`, you will see a ``vsim-FLI-3155`` error:

.. code-block:: bash

    ** Error (suppressible): (vsim-FLI-3155) The FLI is not enabled in this version of ModelSim.

ModelSim DE and SE (and Questa, of course) support the :term:`FLI`.

In order to start ModelSim or Questa with the graphical interface and for the simulator to remain active after the tests have completed, set :make:var:`GUI=1`.
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

In order to use this simulator, set :make:var:`SIM` to ``ghdl``:

.. code-block:: bash

    make SIM=ghdl

Noteworthy is that despite GHDL being a VHDL simulator, it implements the :term:`VPI` interface.

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

    SIM_ARGS=--vcd=anyname.vhd make SIM=ghdl

A VCD file named :file:`anyname.vcd` will be generated in the current directory.

:make:var:`SIM_ARGS` can also be used to pass command line arguments related to :ref:`other waveform formats supported by GHDL <ghdl:export_waves>`.


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
