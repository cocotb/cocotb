module testbench (
    input  logic        clk,
    input  logic        data_in,
    output logic        data_out
);

dut i_dut (
    .clk                (clk),
    .data_in            (data_in),
    .data_out           (data_out)
);

endmodule
