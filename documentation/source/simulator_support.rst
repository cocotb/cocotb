.. _simulator-support:

*****************
Simulator Support
*****************

This page documents specifics, limitations, workarounds etc. in the various simulators.


.. _sim-icarus:

Icarus
======

.. _sim-icarus-accessing-bits:

Accessing bits in a vector
--------------------------

Accessing bits of a vector doesn't work:

.. code-block:: python3

    dut.stream_in_data[2] <= 1

See the ``access_single_bit`` test in :file:`examples/functionality/tests/test_discovery.py`.

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

.. _sim-icarus-time:

Time unit and precision
-----------------------

Setting the time unit and time precision is not possible from the command-line,
and therefore the make variables :make:var:`COCOTB_HDL_TIMEUNIT` and :make:var:`COCOTB_HDL_TIMEPRECISION` are ignored.


.. _sim-verilator:

Verilator
=========

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

    EXTRA_ARGS += --trace

To set the same options on the command line, use ``EXTRA_ARGS="--trace --trace-structs" make ...``.
A VCD file named ``dump.vcd`` will be generated in the current directory.


.. _sim-vcs:

Synopsys VCS
============

cocotb currently only supports VPI for Synopsys VCS, not VHPI.


.. _sim-aldec:

Aldec Riviera-PRO
=================

.. note::

   On Windows, do not install the C++ compiler, i.e. unselect it during the installation process of Riviera-PRO.
   (A workaround is to remove or rename the ``mingw`` directory located in the Riviera-PRO installation directory.)

The :envvar:`LICENSE_QUEUE` environment variable can be used for this simulator –
this setting will be mirrored in the TCL ``license_queue`` variable to control runtime license checkouts.

.. _sim-activehdl:

Aldec Active-HDL
================


.. _sim-questa:

Mentor Questa
=============

See :ref:`sim-modelsim`.


.. _sim-modelsim:

Mentor ModelSim
===============

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

See :ref:`sim-xcelium`.

.. _sim-xcelium:

Cadence Xcelium
===============

The simulator automatically loads VPI even when only VHPI is requested.


.. _sim-ghdl:

GHDL
====

Support is preliminary.
Noteworthy is that despite GHDL being a VHDL simulator, it implements the VPI interface.

.. _sim-nvc:

NVC
===

To enable display of VHPI traces, use ``SIM_ARGS=--vhpi-trace make ...``.
