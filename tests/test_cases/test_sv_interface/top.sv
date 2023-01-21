// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

`timescale 1us/1us

interface sv_if();
  logic a;
  reg b;
  wire c;
endinterface

module top ();

sv_if sv_if_i();
`ifdef VERILATOR
   logic d; // without this workaround for Verilator, cocotb gets a gpi error 'no root handle found'
`endif
endmodule
