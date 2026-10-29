// Example using mixed-language simulation
//
// Here we have a SystemVerilog toplevel that instantiates both SV and VHDL
// sub entities
module endian_swapper_mixed #(
    parameter                               DATA_BYTES = 8
) (
    input                                   clk,
    input                                   reset_n,

    input [DATA_BYTES*8-1:0]                stream_in_data,
    input [$clog2(DATA_BYTES)-1:0]          stream_in_empty,
    input                                   stream_in_valid,
    input                                   stream_in_startofpacket,
    input                                   stream_in_endofpacket,
    output reg                              stream_in_ready,

    output reg [DATA_BYTES*8-1:0]           stream_out_data,
    output reg [$clog2(DATA_BYTES)-1:0]     stream_out_empty,
    output reg                              stream_out_valid,
    output reg                              stream_out_startofpacket,
    output reg                              stream_out_endofpacket,
    input                                   stream_out_ready,

    input  [1:0]                            csr_address,
    output reg [31:0]                       csr_readdata,
    output reg                              csr_readdatavalid,
    input                                   csr_read,
    input                                   csr_write,
    output reg                              csr_waitrequest,
    input [31:0]                            csr_writedata
);

logic [DATA_BYTES*8-1:0]                    sv_to_vhdl_data;
logic [$clog2(DATA_BYTES)-1:0]              sv_to_vhdl_empty;
logic                                       sv_to_vhdl_valid;
logic                                       sv_to_vhdl_startofpacket;
logic                                       sv_to_vhdl_endofpacket;
logic                                       sv_to_vhdl_ready;

logic                                       csr_waitrequest_sv;
logic                                       csr_waitrequest_vhdl;


endian_swapper_sv #(
    .DATA_BYTES                             (DATA_BYTES)
) i_swapper_sv (
    .clk                                    (clk),
    .reset_n                                (reset_n),

    .stream_in_empty                        (stream_in_empty),
    .stream_in_data                         (stream_in_data),
    .stream_in_endofpacket                  (stream_in_endofpacket),
    .stream_in_startofpacket                (stream_in_startofpacket),
    .stream_in_valid                        (stream_in_valid),
    .stream_in_ready                        (stream_in_ready),

    .stream_out_empty                       (sv_to_vhdl_empty),
    .stream_out_data                        (sv_to_vhdl_data),
    .stream_out_endofpacket                 (sv_to_vhdl_endofpacket),
    .stream_out_startofpacket               (sv_to_vhdl_startofpacket),
    .stream_out_valid                       (sv_to_vhdl_valid),
    .stream_out_ready                       (sv_to_vhdl_ready),

    .csr_address                            (csr_address),
    .csr_readdata                           (csr_readdata),
    .csr_readdatavalid                      (csr_readdatavalid),
    .csr_read                               (csr_read),
    .csr_write                              (csr_write),
    .csr_waitrequest                        (csr_waitrequest_sv),
    .csr_writedata                          (csr_writedata)
);


endian_swapper_vhdl #(
    .DATA_BYTES                             (DATA_BYTES)
) i_swapper_vhdl (
    .clk                                    (clk),
    .reset_n                                (reset_n),

    .stream_in_empty                        (sv_to_vhdl_empty),
    .stream_in_data                         (sv_to_vhdl_data),
    .stream_in_endofpacket                  (sv_to_vhdl_endofpacket),
    .stream_in_startofpacket                (sv_to_vhdl_startofpacket),
    .stream_in_valid                        (sv_to_vhdl_valid),
    .stream_in_ready                        (sv_to_vhdl_ready),

    .stream_out_empty                       (stream_out_empty),
    .stream_out_data                        (stream_out_data),
    .stream_out_endofpacket                 (stream_out_endofpacket),
    .stream_out_startofpacket               (stream_out_startofpacket),
    .stream_out_valid                       (stream_out_valid),
    .stream_out_ready                       (stream_out_ready),

    .csr_address                            (csr_address),
    .csr_readdata                           (),
    .csr_readdatavalid                      (),
    .csr_read                               (csr_read),
    .csr_write                              (csr_write),
    .csr_waitrequest                        (csr_waitrequest_vhdl),
    .csr_writedata                          (~csr_writedata)

);

assign csr_waitrequest = csr_waitrequest_sv | csr_waitrequest_vhdl;

endmodule
