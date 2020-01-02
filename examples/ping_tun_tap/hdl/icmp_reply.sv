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
//
// Simple ICMP echo server to repond to pings.
//
// Does store-and-forward using an array then modifies the checksum in place
//
// Doesn't perform any validation of the packet etc.
//
// Note this is not an example of how to write RTL ;)

module icmp_reply (
    input                                  clk,
    input                                  reset_n,

    input [31:0]                           stream_in_data,
    input [1:0]                            stream_in_empty,
    input                                  stream_in_valid,
    input                                  stream_in_startofpacket,
    input                                  stream_in_endofpacket,
    output reg                             stream_in_ready,

    output reg [31:0]                      stream_out_data,
    output reg [1:0]                       stream_out_empty,
    output reg                             stream_out_valid,
    output reg                             stream_out_startofpacket,
    output reg                             stream_out_endofpacket,
    input                                  stream_out_ready
);

parameter S_IDLE = 3'b000;
parameter S_RECV_PACKET = 3'b001;
parameter S_MODIFY_PACKET = 3'b010;
parameter S_SEND_PACKET = 3'b011;

reg [2:0]       state;
reg [31:0]      packet_buffer [31:0];

reg [4:0]       rx_word_ptr, tx_word_ptr;
reg [1:0]       empty_saved;



always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        state                   <= S_IDLE;
        rx_word_ptr             <= 0;
        tx_word_ptr             <= 0;
        stream_out_valid        <= 1'b0;
        stream_in_ready         <= 1'b0;
    end else begin

        case (state)
            S_IDLE: begin

                stream_in_ready <= 1'b1;

                if (stream_in_startofpacket && stream_in_valid && stream_in_ready) begin
                    state                               <= S_RECV_PACKET;
                    rx_word_ptr                         <= 1;
                    packet_buffer[0]                    <= stream_in_data;
                end
            end

            S_RECV_PACKET: begin
                if (stream_in_valid) begin
                    packet_buffer[rx_word_ptr]          <= stream_in_data;
                    rx_word_ptr                         <= rx_word_ptr + 1;

                    if (stream_in_endofpacket) begin
                        state           <= S_MODIFY_PACKET;
                        stream_in_ready <= 1'b0;
                        empty_saved     <= stream_in_empty;
                    end
                end
            end

            // NB since we do all modification in one cycle this won't
            // synthesise as a RAM - code not intended for actual use
            S_MODIFY_PACKET: begin

                // Swap src/destination addresses
                packet_buffer[3]        <= packet_buffer[4];
                packet_buffer[4]        <= packet_buffer[3];

                // Change the ICMP type to Echo Reply
                packet_buffer[5][7:0]   <= 8'b0;

                // Modify checksum in-place
                packet_buffer[5][31:16] <= packet_buffer[5][31:16] - 16'h0800;

                state                   <= S_SEND_PACKET;
                stream_out_startofpacket<= 1'b1;
                stream_out_empty        <= 0;
            end

            S_SEND_PACKET: begin
                stream_out_valid        <= 1'b1;
                stream_out_data         <= packet_buffer[tx_word_ptr];

                if (stream_out_ready) begin
                    tx_word_ptr                 <= tx_word_ptr + 1;

                    if (tx_word_ptr > 0)
                        stream_out_startofpacket<= 1'b0;

                    if (tx_word_ptr == rx_word_ptr - 1) begin
                        stream_out_empty        <= empty_saved;
                        stream_out_endofpacket  <= 1'b1;
                    end

                    if (tx_word_ptr == rx_word_ptr) begin
                        state                   <= S_IDLE;
                        rx_word_ptr             <= 0;
                        tx_word_ptr             <= 0;
                        stream_out_valid        <= 1'b0;
                        stream_out_endofpacket  <= 1'b0;
                    end

                end
            end
          default: begin
             state <= S_IDLE;
          end
        endcase
    end
end

`ifdef COCOTB_SIM
`ifndef VERILATOR // traced differently
initial begin
  $dumpfile ("waveform.vcd");
  $dumpvars (0,icmp_reply);
  #1 $display("Sim running...");
end
`endif
`endif

endmodule
