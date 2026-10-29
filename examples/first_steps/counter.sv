// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

module counter (
  input  logic clk,
  input  logic rst,
  input  logic ena,
  input  logic set,
  input  logic [7:0] din,
  output logic [7:0] count
);

  timeunit 1ns;
  timeprecision 1ns;

  always_ff @(posedge clk) begin
    if (rst) begin
      count <= 8'd0;
    end else begin
      if (set) begin
        count <= din;
      end else if (ena) begin
        count <= count + 1;
      end else begin
        count <= count;
      end
    end
  end

endmodule
