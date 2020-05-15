// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0
// Adder DUT
`timescale 1ns/1ps

module adder #(
  parameter integer DATA_WIDTH = 4
) (
  input  logic unsigned [DATA_WIDTH-1:0] A,
  input  logic unsigned [DATA_WIDTH-1:0] B,
  output logic unsigned [DATA_WIDTH:0]   X
);

  assign X = A + B;

  // Dump waves
  initial begin
    $dumpfile("dump.vcd");
    $dumpvars(1, adder);
  end

endmodule
