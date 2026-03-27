Mixed-signal (analog/digital)
=============================

This example with two different designs shows
how cocotb can be used in an analog-mixed signal (AMS) simulation,
provided your simulator supports this.
Such an AMS setup involves a digital and an analog simulation kernel,
and also provides means to transfer data between the digital and the analog domain.

The "-AMS" variants of the common digital HDLs (VHDL-AMS, Verilog-AMS and SystemVerilog-AMS)
and languages like Spice can be used to express the analog behavior of your circuit.

Due to limitations of the underlying simulator interfaces (VPI, VHPI, FLI),
cocotb cannot directly access the analog domain but has to resort to e.g. HDL helper code.
Thus, unlike the other examples,
this testbench includes a helper part implemented in HDL.

.. toctree::
   rescap
   regulator
