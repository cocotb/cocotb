// Simple streaming module for profiling
`timescale 1ns/1ps

module bench_module (
    input  logic        clk,
    input  logic [7:0]  stream_in_data,
    input  logic        stream_in_valid,
    output logic        stream_in_ready,
    output logic [7:0]  stream_out_data,
    output logic        stream_out_valid,
    input  logic        stream_out_ready
);

    always @(posedge clk) begin
        stream_out_data  <= stream_in_data;
        stream_out_valid <= stream_in_valid;
        stream_in_ready  <= stream_out_ready;
    end

endmodule
