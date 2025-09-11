// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

module simple_counter (
  input  logic clk,
  input  logic rst,
  input  logic ena,
  input  logic set,
  input  logic [7:0] din,
  output logic [7:0] counter
);

  timeunit 1ns;
  timeprecision 1ns;

  always_ff @(posedge clk or edge rst) begin
    if (rst) begin
      counter <= 8'd0;
    end else begin
      if (set) begin
        counter <= din;
      end else if (ena) begin
        counter <= counter + 1;
      end else begin
        counter <= counter;
      end
    end
  end

endmodule
