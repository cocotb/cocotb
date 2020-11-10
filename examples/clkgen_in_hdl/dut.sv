// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ns

module dut (
  input logic rst_n,
  input logic clk
);

  integer count = 0;

  always @(negedge clk or rst_n) begin
    if (rst_n == 0) begin
      count = 0;
    end else begin
      count = count + 1;
    end
  end

endmodule
