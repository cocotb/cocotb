// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ns

module clkgen (
  input real period_ns,
  input logic start_high,
  output logic clk
);

  real   period_ns_int;
  logic  clk_int;

  initial begin
    if (period_ns == 0.0) begin
      // default value
      period_ns_int = 10.0;
    end else begin
      period_ns_int = period_ns;
    end
    if (start_high == 0) begin
      clk_int = 0;
    end else begin
      clk_int = 1;  // unassigned start_high (==Z) means "do start high"
    end
    forever begin
      #(0.5 * period_ns_int * 1ns);
      clk_int = ~clk_int;
    end
  end

  assign clk = clk_int;

endmodule
