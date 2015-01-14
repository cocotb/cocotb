// Adder DUT
module adder (input [3:0] A,
              input [3:0] B,
              output reg [4:0] X);
  always @(A or B) begin
    X = A + B;
  end

  // Dump waves
  initial begin
    $dumpfile("dump.vcd");
    $dumpvars(1, adder);
  end

endmodule
