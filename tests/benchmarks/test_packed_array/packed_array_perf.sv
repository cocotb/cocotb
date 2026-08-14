// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

parameter int X = 256;
parameter int Y = 256;
parameter int Z = 256;

module packed_array_perf (
    input  logic [X-1:0][Y-1:0] i_wide_2d,
    output logic [X-1:0][Y-1:0] o_wide_2d,

    input  logic [X-1:0][Y-1:0][Z-1:0] i_wide_3d,
    output logic [X-1:0][Y-1:0][Z-1:0] o_wide_3d
);

  assign o_wide_2d = i_wide_2d;
  assign o_wide_3d = i_wide_3d;

endmodule
