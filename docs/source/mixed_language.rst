Mixed Language
==============

The directory :file:`examples/mixed_language/` contains two toplevel :term:`HDL` files,
one in VHDL, one in SystemVerilog, that each instantiate an ``endian_swapper`` entity in
SystemVerilog and VHDL in parallel and chains them together so that the endianness is swapped twice.

Thus, we end up with SystemVerilog+VHDL instantiated in VHDL and
SystemVerilog+VHDL instantiated in SystemVerilog.

The cocotb testbench pulls the reset on both instances and checks that they behave the same.

.. todo::

   This example is not complete.

.. spelling:word-list::
   Todo
