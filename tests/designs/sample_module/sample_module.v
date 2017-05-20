//-----------------------------------------------------------------------------
// Copyright (c) 2013 Potential Ventures Ltd
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

module sample_module (
    input                                       clk,

    output reg                                  stream_in_ready,
    input                                       stream_in_valid,
`ifndef __ICARUS__
    input real                                  stream_in_real,
    input  integer                              stream_in_int,
    output real                                 stream_out_real,
    output integer                              stream_out_int,
    input  test_if                              inout_if,
`endif
    input  [7:0]                                stream_in_data,
    input  [63:0]                               stream_in_data_wide,

    input                                       stream_out_ready,
    output reg [7:0]                            stream_out_data_comb,
    output reg                                  stream_out_valid,
    output reg [7:0]                            stream_out_data_registered,

    output                                      and_output

);

always @(posedge clk)
    stream_out_valid <= stream_in_valid;

always @(posedge clk)
    stream_out_data_registered <= stream_in_data;

always @(stream_in_data)
    stream_out_data_comb = stream_in_data;

always @(stream_in_data)
    stream_out_data_comb = stream_in_data;

always @(stream_out_ready)
    stream_in_ready      = stream_out_ready;

`ifndef __ICARUS__
always @(stream_in_real)
    stream_out_real      = stream_in_real;

always @(stream_in_int)
    stream_out_int <= stream_in_int;

test_if struct_var;
`endif

and test_and_gate(and_output, stream_in_ready, stream_in_valid);

initial begin
     $dumpfile("waveform.vcd");
     $dumpvars(0,sample_module);

//   TODO: Move into a separate test
//     #500000 $fail_test("Test timed out, failing...");
end

reg[3:0] temp;
parameter NUM_OF_MODULES = 4;
genvar idx;
generate
for (idx = 0; idx < NUM_OF_MODULES; idx=idx+1) begin
    always @(posedge clk) begin
        temp[idx] <= 1'b0;
    end
end
endgenerate

endmodule

