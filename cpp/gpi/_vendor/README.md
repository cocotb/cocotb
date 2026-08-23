# Third-party code

This directory contains code from various third parties, which is distributed
together with cocotb. Note that some code may be licensed differently from
cocotb itself; refer to the individual files for details.

## SystemVerilog VPI

The headers `vpi/vpi_user.h` and `vpi/sv_vpi_user.sv` are part of the
SystemVerilog LRM.

## VHPI

The header `vhpi/vhpi_user.h` is part of the VHPI/VHDL standard.

## ModelSim/Questa FLI

The header `fli/mti.h` is part of the Siemens EDA Questa distribution and
distributed under the
[Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).

The header `fli/acc_user.h` defines the PLI ACC (access) routines.
The file is part of the
[Verilog 2001 LRM](https://standards.ieee.org/ieee/1364/2052/) (IEEE 1364-2001),
Annex E, and is shipped in a version as modified by Siemens EDA.

The header `fli/acc_vhdl.h` is a ModelSim/Questa extension to the PLI standard to
support VHDL.

## TCL

The files in the `tcl` directory are part of the
[Tcl 8.6.5 source code](https://www.tcl.tk/software/tcltk/download.html), which
is distributed under a BSD license. Refer to `tcl/license.terms` for details.
