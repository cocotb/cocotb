`timescale 1 ps / 1 ps

module avalon_module (
    input                                       clk,

    output reg                                  stream_in_ready,
    input                                       stream_in_valid,
    input  [7:0]                                stream_in_data,
    input  [63:0]                               stream_in_data_wide,

    input                                       stream_out_ready,
    output reg [7:0]                            stream_out_data_comb,
    output reg [7:0]                            stream_out_data_registered
);

always @(posedge clk)
    stream_out_data_registered <= stream_in_data;

always @(stream_in_data)
    stream_out_data_comb = stream_in_data;

always @(stream_out_ready)
    stream_in_ready      = stream_out_ready;


initial begin
     $dumpfile("waveform.vcd");
     $dumpvars(0,avalon_module);

//   TODO: Move into a separate test
//     #500000 $fail_test("Test timed out, failing...");
end

endmodule
