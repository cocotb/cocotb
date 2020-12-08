// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

`timescale 1 ns / 1 ps

module dual_clock (
  input clk1,
  input clk2
);

integer count1, count2;

initial begin
    count1 = 0;
    count2 = 0;
end

always @(posedge clk1) begin
    count1 <= count1 + 1;
end

always @(posedge clk2) begin
    count2 <= count2 + 1;
end

endmodule
