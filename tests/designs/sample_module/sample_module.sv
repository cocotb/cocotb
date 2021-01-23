//-----------------------------------------------------------------------------
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above copyright
//       notice, this list of conditions and the following disclaimer in the
//       documentation and/or other materials provided with the distribution.
//     * Neither the name of Potential Ventures Ltd,
//       Copyright (c) 2013 SolarFlare Communications Inc nor the
//       names of its contributors may be used to endorse or promote products
//       derived from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
// ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
// DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
// (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
// LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
// ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//-----------------------------------------------------------------------------

`timescale 1 ps / 1 ps

`ifndef __ICARUS__
typedef struct packed
{
    logic a_in;
    logic b_out;
} test_if;
`endif

module sample_module #(
    parameter INT_PARAM = 12,
    parameter REAL_PARAM = 3.14,
    parameter STRING_PARAM = "Test"
)(
    input                                       clk,

    output reg                                  stream_in_ready,
    input                                       stream_in_valid,
`ifndef __ICARUS__
    input  real                                 stream_in_real,
    input  integer                              stream_in_int,
    output real                                 stream_out_real,
    output integer                              stream_out_int,
    input  test_if                              inout_if,
    input  string                               stream_in_string,
`endif
    input  [7:0]                                stream_in_data,
    input  [31:0]                               stream_in_data_dword,
    input  [38:0]                               stream_in_data_39bit,
    input  [63:0]                               stream_in_data_wide,
    input  [127:0]                              stream_in_data_dqword,

    input                                       stream_out_ready,
    output reg [7:0]                            stream_out_data_comb,
    output reg [7:0]                            stream_out_data_registered,

    output                                      and_output

);

`ifndef __ICARUS__
localparam string STRING_LOCALPARAM = "TESTING_LOCALPARAM";

var   string STRING_VAR   = "TESTING_VAR";
const string STRING_CONST = "TESTING_CONST";
`endif

always @(posedge clk)
    stream_out_data_registered <= stream_in_data;

always @(stream_in_data)
    stream_out_data_comb = stream_in_data;

always @(stream_out_ready)
    stream_in_ready      = stream_out_ready;

`ifndef __ICARUS__
always @(stream_in_real)
    stream_out_real      = stream_in_real;

always @(stream_in_int)
    stream_out_int = stream_in_int;

var string stream_in_string_asciival_str;
var int stream_in_string_asciival;
var int stream_in_string_asciival_sum;
`ifndef _VCP  // Aldec Riviera-PRO and Active-HDL
  // workaround for
  // # ELAB2: Fatal Error: ELAB2_0036 Unresolved hierarchical reference to "stream_in_string.len.len" from module "sample_module" (module not found).
`ifndef VERILATOR
always @(stream_in_string) begin
    $display("%m: stream_in_string has been updated, new value is '%s'", stream_in_string);
    stream_in_string_asciival_sum = 0;
    for (int idx = 0; idx < stream_in_string.len(); idx=idx+1) begin
        stream_in_string_asciival_str = $sformatf("%0d", stream_in_string[idx]);
        stream_in_string_asciival = stream_in_string_asciival_str.atoi();
        stream_in_string_asciival_sum += stream_in_string_asciival;
        $display("%m: idx=%0d, stream_in_string_asciival=%0d -> stream_in_string_asciival_sum=%0d",
                 idx, stream_in_string_asciival, stream_in_string_asciival_sum);
    end
end
`endif //  `ifndef VERILATOR
`endif //  `ifndef _VCP

test_if struct_var;
`endif //  `ifndef __ICARUS__

and test_and_gate(and_output, stream_in_ready, stream_in_valid);

initial begin
    $dumpfile("waveform.vcd");
    $dumpvars(0,sample_module);
end

parameter NUM_OF_MODULES = 4;
reg[NUM_OF_MODULES-1:0] temp;
genvar idx;
generate
    for (idx = 0; idx < NUM_OF_MODULES; idx=idx+1) begin
        always @(posedge clk) begin
            temp[idx] <= 1'b0;
        end
    end
endgenerate

reg [7:0] register_array [1:0];
always @(posedge clk) begin
    // Ensure internal array is not optimized out
    register_array[0] <= 0;
end

//For testing arrays
reg [7:0]  array_7_downto_4[7:4];
reg [7:0]  array_4_to_7[4:7];
reg [7:0]  array_3_downto_0[3:0];
reg [7:0]  array_0_to_3[0:3];
reg [7:0]  array_2d[0:1][31:28];
always @(posedge stream_in_valid) begin
    // Ensure internal array is not optimized out
    array_7_downto_4[4] <= 0;
    array_4_to_7[7] <= 0;
    array_3_downto_0[0] <= 0;
    array_0_to_3[3] <= 0;
    array_2d[1][28] <= 0;
end

//For testing type assigned to logic
logic logic_a, logic_b, logic_c;
assign logic_a = stream_in_valid;
always@* logic_b = stream_in_valid;
always@(posedge clk) logic_c <= stream_in_valid;

reg _underscore_name;
`ifdef __ICARUS__
    // By default, a variable must be used in some way in order
    // to be visible to VPI in Icarus Verilog.
    // See https://github.com/steveicarus/iverilog/issues/322
    assign _underscore_name = 0;
`endif

bit mybit;
bit [1:0] mybits;
bit [1:0] mybits_uninitialized;
initial begin
    mybit = 1;
    mybits = '1;
end

`ifndef VERILATOR
always @(*) begin
    $display("%m: mybit has been updated, new value is %b", mybit);
end
always @(*) begin
    $display("%m: mybits has been updated, new value is %b", mybits);
end
always @(*) begin
    $display("%m: mybits_uninitialized has been updated, new value is %b", mybits_uninitialized);
end
`endif

endmodule
