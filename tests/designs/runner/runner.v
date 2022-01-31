// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

`include "basic_hierarchy_module.v"

module runner #(
    parameter WIDTH_IN = 4,
    parameter WIDTH_OUT = 8
) (
    input  [WIDTH_IN-1:0]   data_in,
    output [WIDTH_OUT-1:0]  data_out,
    output [`DEFINE-1:0] define_out
);

basic_hierarchy_module  basic_hierarchy_module(.clk(1'b0), .reset(1'b0));

endmodule
