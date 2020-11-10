// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ns

module tb ();

  clkgen clkgen_inst
    (.period_ns  (period_ns),
     .start_high (start_high),
     .clk        (clk));

  dut dut_inst
    (.clk (clk));

endmodule
