*************
More Examples
*************

Apart from the examples covered with full tutorials in the previous sections,
the directory :file:`cocotb/examples/` contains some more smaller modules you may want to take a look at.


Adder
=====

The directory :file:`cocotb/examples/adder/` contains an ``adder`` :term:`RTL` in both Verilog and VHDL,
an ``adder_model`` implemented in Python,
and the cocotb testbench with two defined tests ­ a simple :func:`adder_basic_test` and
a slightly more advanced :func:`adder_randomised_test`.

This example does not use any :class:`.Driver`, :class:`.Monitor`, or :class:`.Scoreboard`; not even a clock.


D Flip-Flop
===========

The directory :file:`cocotb/examples/dff/` contains a simple D flip-flop, implemented in both VDHL and Verilog.

The :term:`HDL` has the data input port ``d``, the clock port ``c``, and the data output ``q`` with an initial state of ``0``.
No reset port exists.

The cocotb testbench checks the initial state first, then applies random data to the data input.
The flip-flop output is captured at each rising edge of the clock and compared to the applied input data using a :class:`.Scoreboard`.

The testbench defines a ``BitMonitor`` (a sub-class of :class:`.Monitor`) as a pendant to the cocotb-provided :class:`.BitDriver`.
The :class:`.BitDriver`'s  :meth:`~.BitDriver.start` and  :meth:`~.BitDriver.stop` methods are used
to start and stop generation of input data.

A :class:`.TestFactory` is used to generate the random tests.


Mean
====

The directory :file:`cocotb/examples/mean/` contains a module that calculates the mean value of a
data input bus ``i`` (with signals ``i_data`` and ``i_valid``) and
outputs it on ``o`` (with ``i_data`` and ``o_valid``).

It has implementations in both VHDL and SystemVerilog.

The testbench defines a ``StreamBusMonitor`` (a sub-class of :class:`.BusMonitor`), a clock generator,
a ``value_test`` helper coroutine and a few tests.
Test ``mean_randomised_test`` uses the ``StreamBusMonitor`` to
feed a :class:`.Scoreboard` with the collected transactions on input bus ``i``.

Mixed Language
==============

The directory :file:`cocotb/examples/mixed_language/` contains two toplevel :term:`HDL` files,
one in VHDL, one in SystemVerilog, that each instantiate the ``endian_swapper`` in
SystemVerilog and VHDL in parallel and chains them together so that the endianness is swapped twice.

Thus, we end up with SystemVerilog+VHDL instantiated in VHDL and
SystemVerilog+VHDL instantiated in SystemVerilog.

The cocotb testbench pulls the reset on both instances and checks that they behave the same.

.. todo::

   This example is not complete.

.. spelling::
   Todo


AXI Lite Slave
==============

The directory :file:`cocotb/examples/axi_lite_slave/` contains ...

.. todo::

    Write documentation, see :file:`README.md`
