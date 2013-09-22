/*

Endian swapping module.

Simple example with Avalon streaming interfaces and a CSR bus

Exposes 2 32-bit registers via the Avalon-MM interface

   Address 0:  bit     0  [R/W] byteswap enable
               bits 31-1: [N/A] reserved
   Adress  1:  bits 31-0: [RO]  packet count

*/

module endian_swapper #(
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

reg in_packet;
reg byteswapping;
reg [31:0] packet_count;

function [DATA_BYTES*8-1:0] byteswap(input [DATA_BYTES*8-1:0] data);

/*
    // FIXME Icarus doesn't seem to like this....
    reg [$clog2(DATA_BYTES)-1:0] i;

    for (i=0; i<DATA_BYTES; i=i+1)
        byteswap[i*8+7 -:8] = data[(DATA_BYTES-i)*8-1 -:8];
*/
    byteswap = { data[7:0],
                 data[15:8],
                 data[23:16],
                 data[31:24],
                 data[39:32],
                 data[47:40],
                 data[55:48],
                 data[63:56]};
endfunction



always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        stream_out_valid <= 1'b0;
        in_packet        <= 1'b0;
        packet_count     <= 32'd0;
    end else begin

        stream_out_valid             <= stream_in_valid;

        if (stream_out_ready) begin
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



always @(reset_n, stream_in_startofpacket, stream_in_valid)
    csr_waitrequest = !reset_n || in_packet || (stream_in_startofpacket & stream_in_valid);


// Workaround Icarus bug where a simple assign doesn't work
always @(stream_out_ready)
    stream_in_ready = stream_out_ready;


always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        byteswapping <= 1'b0;
    end else begin
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
initial begin                                                                                                    
  $dumpfile ("waveform.vcd");
  $dumpvars (0,endian_swapper);
end
`endif

endmodule

