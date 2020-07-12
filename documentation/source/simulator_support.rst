.. _simulator-support:

*****************
Simulator Support
*****************

This page lists the simulators that cocotb can be used with
and documents specifics, limitations, workarounds etc.


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

    dut.stream_in_data[2] <= 1

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


.. _sim-verilator:

Verilator
=========

In order to use this simulator, set :make:var:`SIM` to ``verilator``:

.. code-block:: bash

    make SIM=verilator

cocotb supports Verilator 4.020 and above.
Verilator converts Verilog code to C++ code that is compiled.
It does not support VHDL.
One major limitation compared to standard Verilog simulators is that it does not support delayed assignments.

To run cocotb with Verilator, you need ``verilator`` in your PATH.

Finally, cocotb currently generates a Verilator toplevel C++ simulation loop which is timed at the highest precision.
If your design's clocks vary in precision, the performance of the simulation can be improved in the same order of magnitude by adjusting the precision in the Makefile, e.g.,

.. code-block:: makefile

    COCOTB_HDL_TIMEPRECISION = 1us # Set precision to 10^-6s

.. versionadded:: 1.3

Coverage
--------

To enable HDL code coverage, add Verilator's coverage option(s) to the :make:var:`EXTRA_ARGS` make variable, for example:

 .. code-block:: make

    EXTRA_ARGS += --coverage

This will result in coverage data being written to ``coverage.dat``.

.. _sim-verilator-waveforms:

Waveforms
---------

To get waveforms in VCD format, add Verilator's trace option(s) to the
:make:var:`EXTRA_ARGS` make variable, for example in a Makefile:

  .. code-block:: make

    EXTRA_ARGS += --trace --trace-structs

To set the same options on the command line, use ``EXTRA_ARGS="--trace --trace-structs" make ...``.
A VCD file named ``dump.vcd`` will be generated in the current directory.

.. _sim-vcs:

Synopsys VCS
============

In order to use this simulator, set :make:var:`SIM` to ``vcs``:

.. code-block:: bash

    make SIM=vcs

cocotb currently only supports VPI for Synopsys VCS, not VHPI.


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

.. _sim-questa:

Mentor Questa
=============

In order to use this simulator, set :make:var:`SIM` to ``questa``:

.. code-block:: bash

    make SIM=questa

For more information, see :ref:`sim-modelsim`.


.. _sim-modelsim:

Mentor ModelSim
===============

In order to use this simulator, set :make:var:`SIM` to ``modelsim``:

.. code-block:: bash

    make SIM=modelsim

.. note::

   In order to use FLI (for VHDL), a ``vdbg`` executable from the simulator installation directory needs to be available on the ``PATH`` during cocotb installation.
   This is needed to access the proprietary ``mti.h`` header file.

Any ModelSim PE or ModelSim PE derivatives (like the ModelSim Microsemi, Intel, Lattice Editions) do not support the VHDL FLI feature.
If you try to use them with FLI, you will see a ``vsim-FLI-3155`` error:

.. code-block:: bash

    ** Error (suppressible): (vsim-FLI-3155) The FLI is not enabled in this version of ModelSim.

ModelSim DE and SE (and Questa, of course) support the FLI.


.. _sim-incisive:

Cadence Incisive
================

In order to use this simulator, set :make:var:`SIM` to ``ius``:

.. code-block:: bash

    make SIM=ius

For more information, see :ref:`sim-xcelium`.


.. _sim-xcelium:

Cadence Xcelium
===============

In order to use this simulator, set :make:var:`SIM` to ``xcelium``:

.. code-block:: bash

    make SIM=xcelium

The simulator automatically loads VPI even when only VHPI is requested.


.. _sim-ghdl:

GHDL
====

In order to use this simulator, set :make:var:`SIM` to ``ghdl``:

.. code-block:: bash

    make SIM=ghdl

Support is preliminary.
Noteworthy is that despite GHDL being a VHDL simulator, it implements the VPI interface.


.. _sim-cvc:

Tachyon DA CVC
==============

In order to use `Tachyon DA <http://www.tachyon-da.com/>`_'s `CVC <https://github.com/cambridgehackers/open-src-cvc>`_ simulator,
set :make:var:`SIM` to ``cvc``:

.. code-block:: bash

    make SIM=cvc

Note that cocotb's makefile is using CVC's interpreted mode.
