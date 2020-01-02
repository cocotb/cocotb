// Adder DUT

`timescale 1ns/1ps

module adder #(
    parameter   DATA_WIDTH = 4
) (
    input      [DATA_WIDTH-1:0] A,
    input      [DATA_WIDTH-1:0] B,
    output reg [DATA_WIDTH:0] X
    );

  always @(A or B) begin
    X = A + B;
  end

`ifndef VERILATOR // traced differently
  // Dump waves
  initial begin
    $dumpfile("dump.vcd");
    $dumpvars(1, adder);
  end
`endif

endmodule
