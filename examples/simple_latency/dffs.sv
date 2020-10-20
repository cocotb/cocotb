// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

`timescale 1us/1us

module dffs (
  input  logic clk, 
  input  logic d,
  output logic q,

  input  logic [2:0] delayed_d,
  output logic [2:0] delayed_q
);

always @(posedge clk) begin
  q <= d;
  delayed_q <= delayed_d;
end
  
initial begin
  $dumpfile ("sim_results.fst");
  $dumpvars (0, dffs);
  #1;
end

endmodule
