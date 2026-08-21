// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

typedef enum logic [1:0] {
  COLOR_RED   = 2'd0,
  COLOR_GREEN = 2'd1,
  COLOR_BLUE  = 2'd2,
  COLOR_WHITE = 2'd3
} color_e;

typedef union packed {
  logic [15:0] raw;
  struct packed {
    logic [7:0] hi;
    logic [7:0] lo;
  } halves;
} word_u;

typedef struct packed {
  logic [1:0] pkg_id;
  logic       die;
  logic [1:0] tile;
} noc_id_t;  // width 5

typedef struct packed {
  logic [11:0] seq_idx;
  noc_id_t     dst;
  logic [4:0]  dst_local;
} noc_hdr_t;  // width 12 + 5 + 5 = 22


module packed_array (
    input logic clk,

    // 2-D packed logic array.
    input  logic [7:0][3:0] i_packed,
    input  logic i_unpacked [7:0][3:0],
    input  logic  [2:0][5:0] i_mixed [7:0][3:0],
    input  logic  [2:0] i_short,
    input  logic  i_bit,

    output logic [7:0][3:0] o_packed,

    // 3-D packed logic array.
    input  logic [1:0][2:0][3:0] i_packed_3d,
    output logic [1:0][2:0][3:0] o_packed_3d,

    // Packed arrays with non-zero and mixed-direction ranges.
    /* verilator lint_off ASCRANGE */
    input  logic [5:4][0:2][1:-1] i_packed_mixed,
    output logic [5:4][0:2][1:-1] o_packed_mixed,
    /* verilator lint_on ASCRANGE */

    input logic [0:0][31:0] i_packed_32,
    output logic [0:0][31:0] o_packed_32,
    input logic [1:0][1:0][1:0][32:0] i_packed_wide,
    output logic [1:0][1:0][1:0][32:0] o_packed_wide,

    // 2-D packed array of packed enums.
    input  color_e [1:0][3:0] i_enum_arr2d,
    output color_e [1:0][3:0] o_enum_arr2d,

    // 2-D packed array of packed unions.
    input  word_u [1:0][3:0] i_union_arr2d,
    output word_u [1:0][3:0] o_union_arr2d,

    // 2-D packed array of packed structs.
    input  noc_hdr_t [1:0][3:0] i_pkt_arr2d,
    output noc_hdr_t [1:0][3:0] o_pkt_arr2d,

    input  color_e  i_enum_arr2d_unpk[1:0][3:0],
    input  word_u  i_union_arr2d_unpk[1:0][3:0],
    input  noc_hdr_t i_pkt_arr2d_unpk[1:0][3:0]
);

  assign o_packed       = i_packed;
  assign o_packed_3d    = i_packed_3d;
  assign o_packed_mixed = i_packed_mixed;
  assign o_packed_32    = i_packed_32;
  assign o_packed_wide  = i_packed_wide;
  assign o_enum_arr2d   = i_enum_arr2d;
  assign o_union_arr2d  = i_union_arr2d;
  assign o_pkt_arr2d    = i_pkt_arr2d;

endmodule
