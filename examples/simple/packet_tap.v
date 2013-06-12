//-----------------------------------------------------------------------------
// Copyright (c) 2013 Potential Ventures Ltd
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above copyright
//       notice, this list of conditions and the following disclaimer in the
//       documentation and/or other materials provided with the distribution.
//     * Neither the name of Potential Ventures Ltd nor the
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

module pv_packet_tap (
    input                                       clk,
    input                                       reset_n,

    // Stream_in bus
    input                                       stream_in_startofpacket,
    input                                       stream_in_endofpacket,
    input                                       stream_in_valid,
    output                                      stream_in_ready,
    input  [71:0]                               stream_in_data,
    input  [2:0]                                stream_in_empty,
    input  [1:0]                                stream_in_error,
    input                                       stream_in_channel,

    // Stream_out bus
    output reg                                  stream_out_startofpacket,
    output reg                                  stream_out_endofpacket,
    output reg                                  stream_out_valid,
    input                                       stream_out_ready,
    output reg [71:0]                           stream_out_data,
    output reg [2:0]                            stream_out_empty,
    output reg [1:0]                            stream_out_error,
    output reg                                  stream_out_channel,

    // Tap point
    output                                      tap_out_startofpacket,
    output                                      tap_out_endofpacket,
    output                                      tap_out_valid,
    input                                       tap_out_ready,
    output  [71:0]                              tap_out_data,
    output  [2:0]                               tap_out_empty,
    output  [1:0]                               tap_out_error,
    output                                      tap_out_channel,


    // Avalon-MM interface
    input  [6:0]                                csr_address,
    output [31:0]                               csr_readdata,
    input                                       csr_read,
    input                                       csr_write,
    output                                      csr_waitrequest,
    input  [31:0]                               csr_writedata
);

// Cross-wire the Avalon-ST bus
always @(posedge clk) begin
    stream_out_startofpacket <= stream_in_startofpacket;
    stream_out_endofpacket   <= stream_in_endofpacket;
    stream_out_valid         <= stream_in_valid;      
    stream_out_data          <= stream_in_data;
    stream_out_empty         <= stream_in_empty;
    stream_out_error         <= stream_in_error;
    stream_out_channel       <= stream_in_channel;
end

// assign stream_out_startofpacket = stream_in_startofpacket;
// assign stream_out_endofpacket   = stream_in_endofpacket;
// assign stream_out_valid         = stream_in_valid;      
// assign stream_out_data          = stream_in_data;
// assign stream_out_empty         = stream_in_empty;
// assign stream_out_error         = stream_in_error;
// assign stream_out_channel       = stream_in_channel;


// For now just tap everything
assign tap_out_startofpacket    = stream_in_startofpacket;
assign tap_out_endofpacket      = stream_in_endofpacket;
assign tap_out_valid            = stream_in_valid;
assign tap_out_data             = stream_in_data;
assign tap_out_empty            = stream_in_empty;
assign tap_out_error            = stream_in_error;
assign tap_out_channel          = stream_in_channel;

assign stream_in_ready          = stream_out_ready & tap_out_ready;


initial begin
     $dumpfile("waveform.vcd");
     $dumpvars(0,pv_packet_tap);
end


endmodule
