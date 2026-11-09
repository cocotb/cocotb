// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

`timescale 1us/1us

interface sv_if();
  logic a;
  reg b;
  wire c;
  int value;
  int data[2][3];

  modport mp (input a, output b);
endinterface

// Port and connection bounds may differ; elements connect left-to-left.
// Names use <port form>_to_<concrete form>; size denotes [n].
module sub (
  sv_if sv_if_ref_scalar_to_scalar,
  sv_if sv_if_ref_size_to_size[3],
  sv_if.mp sv_if_modport_ref_scalar_to_scalar,
  sv_if sv_if_ref_size_to_size_alt[2],
  sv_if sv_if_ref_size_to_dn[3],
  sv_if sv_if_ref_size_to_size_slice[2],

  sv_if sv_if_ref_size_to_dn_slice[2],
  sv_if sv_if_ref_size_to_size_one_slice[1],
  sv_if sv_if_ref_size_to_dn_one_slice[1],
  sv_if sv_if_ref_scalar_to_size,
  sv_if sv_if_ref_scalar_to_dn,

  sv_if sv_if_ref_up_to_size[0:2],
  sv_if sv_if_ref_up_to_dn[0:2],
  sv_if sv_if_ref_dn_to_size[2:0],
  sv_if sv_if_ref_dn_to_dn[2:0],
  sv_if sv_if_ref_offset_up_to_size[1:3],
  sv_if sv_if_ref_offset_dn_to_dn[3:1],
  sv_if sv_if_ref_far_up_to_size[100:102],
  sv_if sv_if_ref_neg_up_to_size[-1:1],
  sv_if sv_if_ref_allneg_up_to_dn[-3:-1],

  sv_if sv_if_ref_size_to_up[3],
  sv_if sv_if_ref_up_to_up[0:2],
  sv_if sv_if_ref_dn_to_up[2:0],
  sv_if sv_if_ref_offset_up_to_up[1:3],
  sv_if sv_if_ref_neg_up_to_up[-1:1],
  sv_if.mp sv_if_modport_ref_dn_to_up[2:0],
  sv_if sv_if_ref_scalar_to_up,
  sv_if.mp sv_if_modport_ref_scalar_to_up
);
  // Keep the ports visible through VPI.
  /* verilator public_module */
  logic sub_sig;
endmodule

module top ();

sv_if sv_if_i();

sv_if sv_if_arr_size[3]();
sv_if sv_if_arr_up[0:2]();

sv_if unrelated_name_arr_size[2]();

sv_if sv_if_arr_dn[2:0]();

sub sub_i (
  .sv_if_ref_scalar_to_scalar(sv_if_i),
  .sv_if_ref_size_to_size(sv_if_arr_size),
  .sv_if_modport_ref_scalar_to_scalar(sv_if_i),
  .sv_if_ref_size_to_size_alt(unrelated_name_arr_size),
  .sv_if_ref_size_to_dn(sv_if_arr_dn),
  .sv_if_ref_size_to_size_slice(sv_if_arr_size[1:2]),
  .sv_if_ref_size_to_dn_slice(sv_if_arr_dn[2:1]),
  .sv_if_ref_size_to_size_one_slice(sv_if_arr_size[2:2]),
  .sv_if_ref_size_to_dn_one_slice(sv_if_arr_dn[1:1]),
  .sv_if_ref_scalar_to_size(sv_if_arr_size[1]),
  .sv_if_ref_scalar_to_dn(sv_if_arr_dn[1]),
  .sv_if_ref_up_to_size(sv_if_arr_size),
  .sv_if_ref_up_to_dn(sv_if_arr_dn),
  .sv_if_ref_dn_to_size(sv_if_arr_size),
  .sv_if_ref_dn_to_dn(sv_if_arr_dn),
  .sv_if_ref_offset_up_to_size(sv_if_arr_size),
  .sv_if_ref_offset_dn_to_dn(sv_if_arr_dn),
  .sv_if_ref_far_up_to_size(sv_if_arr_size),
  .sv_if_ref_neg_up_to_size(sv_if_arr_size),
  .sv_if_ref_allneg_up_to_dn(sv_if_arr_dn),
  .sv_if_ref_size_to_up(sv_if_arr_up),
  .sv_if_ref_up_to_up(sv_if_arr_up),
  .sv_if_ref_dn_to_up(sv_if_arr_up),
  .sv_if_ref_offset_up_to_up(sv_if_arr_up),
  .sv_if_ref_neg_up_to_up(sv_if_arr_up),
  .sv_if_modport_ref_dn_to_up(sv_if_arr_up),
  .sv_if_ref_scalar_to_up(sv_if_arr_up[1]),
  .sv_if_modport_ref_scalar_to_up(sv_if_arr_up[2])
);

endmodule
