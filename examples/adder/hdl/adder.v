// Adder DUT
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

  // Dump waves
  initial begin
    $dumpfile("dump.vcd");
    $dumpvars(1, adder);
  end

endmodule
