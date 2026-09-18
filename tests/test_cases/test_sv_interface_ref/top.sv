// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

`timescale 1us/1us

interface sv_if();
  logic a;
  reg b;
  wire c;

  modport mp (input a, output b);
endinterface

// Takes interfaces as ports. Through VPI these ports are references
// (vpiRefObj) to the interface instances in top, not interfaces in their own
// right, so they must be resolved to their target before use.
module sub (
  sv_if sv_if_ref,
  sv_if sv_if_ref_arr[3],
  sv_if.mp sv_if_modport_ref
);
  // Keep the module from being inlined away, so the reference ports remain
  // visible through VPI.
  /* verilator public_module */
  logic sub_sig;
endmodule

module top ();

sv_if sv_if_i();

sv_if sv_if_arr[3]();

sub sub_i (
  .sv_if_ref(sv_if_i),
  .sv_if_ref_arr(sv_if_arr),
  .sv_if_modport_ref(sv_if_i)
);

endmodule
