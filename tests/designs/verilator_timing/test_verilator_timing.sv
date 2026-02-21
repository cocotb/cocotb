// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module test_verilator_timing (
`ifdef TEST_CLK_EXTERNAL
    input  logic clk,
`endif  // `ifdef TEST_CLK_EXTERNAL
    input  logic d,
    output logic q
);

`ifndef TEST_CLK_EXTERNAL
  // Clocking
  bit clk;
  initial clk = 0;
  always #5 clk = ~clk;
`endif  // `ifndef TEST_CLK_EXTERNAL

  always_ff @(posedge clk) begin : proc_dff
    q <= d;
  end

endmodule : test_verilator_timing
