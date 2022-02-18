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

/*

Endian swapping module.

Simple example with Avalon streaming interfaces and a CSR bus

Avalon-ST has readyLatency of 0
Avalon-MM has fixed readLatency of 1

Exposes 2 32-bit registers via the Avalon-MM interface

   Address 0:  bit     0  [R/W] byteswap enable
               bits 31-1: [N/A] reserved
   Adress  1:  bits 31-0: [RO]  packet count

*/

`timescale 1ns/1ps

module endian_swapper_sv #(
    parameter                              DATA_BYTES = 8
) (
    input                                  clk,
    input                                  reset_n,

    input [DATA_BYTES*8-1:0]               stream_in_data,
    input [$clog2(DATA_BYTES)-1:0]         stream_in_empty,
    input                                  stream_in_valid,
    input                                  stream_in_startofpacket,
    input                                  stream_in_endofpacket,
    output reg                             stream_in_ready,

    output reg [DATA_BYTES*8-1:0]          stream_out_data,
    output reg [$clog2(DATA_BYTES)-1:0]    stream_out_empty,
    output reg                             stream_out_valid,
    output reg                             stream_out_startofpacket,
    output reg                             stream_out_endofpacket,
    input                                  stream_out_ready,

    input  [1:0]                           csr_address,
    output reg [31:0]                      csr_readdata,
    output reg                             csr_readdatavalid,
    input                                  csr_read,
    input                                  csr_write,
    output reg                             csr_waitrequest,
    input [31:0]                           csr_writedata
);



function [DATA_BYTES*8-1:0] byteswap(input [DATA_BYTES*8-1:0] data);
/*
    // FIXME Icarus doesn't seem to like this....
    reg [$clog2(DATA_BYTES)-1:0] i;

    for (i=0; i<DATA_BYTES; i=i+1)
        byteswap[i*8+7 -:8] = data[(DATA_BYTES-i)*8-1 -:8];
*/

    // Hardwire for now
    byteswap = { data[7:0],
                 data[15:8],
                 data[23:16],
                 data[31:24],
                 data[39:32],
                 data[47:40],
                 data[55:48],
                 data[63:56]};
endfunction


reg flush_pipe;
reg in_packet;
reg byteswapping;
reg [31:0] packet_count;


always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        flush_pipe       <= 1'b0;
        in_packet        <= 1'b0;
        packet_count     <= 32'd0;

        stream_out_startofpacket <= 1'b1;
        stream_out_endofpacket   <= 1'b1;
    end else begin

        if (flush_pipe & stream_out_ready)
            flush_pipe <= stream_in_endofpacket & stream_in_valid & stream_out_ready;
        else if (!flush_pipe)
            flush_pipe <= stream_in_endofpacket & stream_in_valid & stream_out_ready;

        if (stream_out_ready & stream_in_valid) begin
            stream_out_empty         <= stream_in_empty;
            stream_out_startofpacket <= stream_in_startofpacket;
            stream_out_endofpacket   <= stream_in_endofpacket;

            if (!byteswapping)
                stream_out_data      <= stream_in_data;
            else
                stream_out_data      <= byteswap(stream_in_data);

            if (stream_in_startofpacket && stream_in_valid) begin
                packet_count <= packet_count + 1;
                in_packet    <= 1'b1;
            end

            if (stream_in_endofpacket && stream_in_valid)
                in_packet    <= 1'b0;

        end
    end
end

always @(*)
    stream_out_valid = (stream_in_valid & ~stream_out_endofpacket) | flush_pipe;


// Hold off CSR accesses during packet transfers to prevent changing of
// endian configuration mid-packet
always @(*)
    csr_waitrequest = !reset_n || in_packet || (stream_in_startofpacket & stream_in_valid) || flush_pipe;


// Workaround Icarus bug where a simple assign doesn't work
always @(stream_out_ready)
    stream_in_ready = stream_out_ready;


always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        byteswapping      <= 1'b0;
        csr_readdatavalid <= 1'b0;
    end else begin
        csr_readdatavalid <= 1'b0;
        if (csr_read) begin
            csr_readdatavalid <= !csr_waitrequest;
            case (csr_address)
                0:    csr_readdata <= {31'b0, byteswapping};
                1:    csr_readdata <= packet_count;
            endcase
        end else if (csr_write & !csr_waitrequest) begin
            case (csr_address)
                0:    byteswapping <= csr_writedata[0];
            endcase
        end
    end
end

`ifdef COCOTB_SIM
`ifndef VERILATOR // traced differently
initial begin
  $dumpfile ("waveform.vcd");
  $dumpvars (0,endian_swapper_sv);
  #1;
end
`endif
`endif

endmodule
