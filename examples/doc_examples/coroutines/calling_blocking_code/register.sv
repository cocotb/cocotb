// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

// simple 8 bit register
module register(
  input logic clk,
  input logic [7:0] register_in,
  input logic write_enable,
  output logic [7:0] register_out
);

  timeunit 1ns;
  timeprecision 1ns;

  logic [7:0] register_internal;

  // Initialize the register to 0
  initial begin
    register_internal = 8'h00;
  end

  always_ff @(posedge clk) begin
    if (write_enable) begin
      register_internal <= register_in;
    end
  end

  assign register_out = register_internal;

endmodule
