// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

/*
Test the verilog dumpfile and dumpargs in combination with cocotb
*/

`timescale 1ns / 1ps

module test_dumpfile_verilator (
    input clk,
    input reset_n
);

  reg [31:0] counter;

  always_ff @(posedge clk) begin
    if (!reset_n) begin
      counter <= 32'h0;
    end else begin
      counter <= counter + 1;
    end
  end

  initial begin
    $dumpfile("waves.vcd");
    $dumpvars(0, test_custom_vcd);
  end

endmodule
