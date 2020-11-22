/*

Copyright (c) 2018 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

*/

// Language: Verilog 2001

`timescale 1ns / 1ps

/*
 * AXI4 interconnect
 */
module axi_interconnect #
(
    // Number of AXI inputs (slave interfaces)
    parameter S_COUNT = 4,
    // Number of AXI outputs (master interfaces)
    parameter M_COUNT = 4,
    // Width of data bus in bits
    parameter DATA_WIDTH = 32,
    // Width of address bus in bits
    parameter ADDR_WIDTH = 32,
    // Width of wstrb (width of data bus in words)
    parameter STRB_WIDTH = (DATA_WIDTH/8),
    // Width of ID signal
    parameter ID_WIDTH = 8,
    // Propagate awuser signal
    parameter AWUSER_ENABLE = 0,
    // Width of awuser signal
    parameter AWUSER_WIDTH = 1,
    // Propagate wuser signal
    parameter WUSER_ENABLE = 0,
    // Width of wuser signal
    parameter WUSER_WIDTH = 1,
    // Propagate buser signal
    parameter BUSER_ENABLE = 0,
    // Width of buser signal
    parameter BUSER_WIDTH = 1,
    // Propagate aruser signal
    parameter ARUSER_ENABLE = 0,
    // Width of aruser signal
    parameter ARUSER_WIDTH = 1,
    // Propagate ruser signal
    parameter RUSER_ENABLE = 0,
    // Width of ruser signal
    parameter RUSER_WIDTH = 1,
    // Propagate ID field
    parameter FORWARD_ID = 0,
    // Number of regions per master interface
    parameter M_REGIONS = 1,
    // Master interface base addresses
    // M_COUNT concatenated fields of M_REGIONS concatenated fields of ADDR_WIDTH bits
    // set to zero for default addressing based on M_ADDR_WIDTH
    parameter M_BASE_ADDR = 0,
    // Master interface address widths
    // M_COUNT concatenated fields of M_REGIONS concatenated fields of 32 bits
    parameter M_ADDR_WIDTH = {M_COUNT{{M_REGIONS{32'd24}}}},
    // Read connections between interfaces
    // M_COUNT concatenated fields of S_COUNT bits
    parameter M_CONNECT_READ = {M_COUNT{{S_COUNT{1'b1}}}},
    // Write connections between interfaces
    // M_COUNT concatenated fields of S_COUNT bits
    parameter M_CONNECT_WRITE = {M_COUNT{{S_COUNT{1'b1}}}},
    // Secure master (fail operations based on awprot/arprot)
    // M_COUNT bits
    parameter M_SECURE = {M_COUNT{1'b0}}
)
(
    input  wire                            clk,
    input  wire                            rst,

    /*
     * AXI slave interfaces
     */
    input  wire [S_COUNT*ID_WIDTH-1:0]     s_axi_awid,
    input  wire [S_COUNT*ADDR_WIDTH-1:0]   s_axi_awaddr,
    input  wire [S_COUNT*8-1:0]            s_axi_awlen,
    input  wire [S_COUNT*3-1:0]            s_axi_awsize,
    input  wire [S_COUNT*2-1:0]            s_axi_awburst,
    input  wire [S_COUNT-1:0]              s_axi_awlock,
    input  wire [S_COUNT*4-1:0]            s_axi_awcache,
    input  wire [S_COUNT*3-1:0]            s_axi_awprot,
    input  wire [S_COUNT*4-1:0]            s_axi_awqos,
    input  wire [S_COUNT*AWUSER_WIDTH-1:0] s_axi_awuser,
    input  wire [S_COUNT-1:0]              s_axi_awvalid,
    output wire [S_COUNT-1:0]              s_axi_awready,
    input  wire [S_COUNT*DATA_WIDTH-1:0]   s_axi_wdata,
    input  wire [S_COUNT*STRB_WIDTH-1:0]   s_axi_wstrb,
    input  wire [S_COUNT-1:0]              s_axi_wlast,
    input  wire [S_COUNT*WUSER_WIDTH-1:0]  s_axi_wuser,
    input  wire [S_COUNT-1:0]              s_axi_wvalid,
    output wire [S_COUNT-1:0]              s_axi_wready,
    output wire [S_COUNT*ID_WIDTH-1:0]     s_axi_bid,
    output wire [S_COUNT*2-1:0]            s_axi_bresp,
    output wire [S_COUNT*BUSER_WIDTH-1:0]  s_axi_buser,
    output wire [S_COUNT-1:0]              s_axi_bvalid,
    input  wire [S_COUNT-1:0]              s_axi_bready,
    input  wire [S_COUNT*ID_WIDTH-1:0]     s_axi_arid,
    input  wire [S_COUNT*ADDR_WIDTH-1:0]   s_axi_araddr,
    input  wire [S_COUNT*8-1:0]            s_axi_arlen,
    input  wire [S_COUNT*3-1:0]            s_axi_arsize,
    input  wire [S_COUNT*2-1:0]            s_axi_arburst,
    input  wire [S_COUNT-1:0]              s_axi_arlock,
    input  wire [S_COUNT*4-1:0]            s_axi_arcache,
    input  wire [S_COUNT*3-1:0]            s_axi_arprot,
    input  wire [S_COUNT*4-1:0]            s_axi_arqos,
    input  wire [S_COUNT*ARUSER_WIDTH-1:0] s_axi_aruser,
    input  wire [S_COUNT-1:0]              s_axi_arvalid,
    output wire [S_COUNT-1:0]              s_axi_arready,
    output wire [S_COUNT*ID_WIDTH-1:0]     s_axi_rid,
    output wire [S_COUNT*DATA_WIDTH-1:0]   s_axi_rdata,
    output wire [S_COUNT*2-1:0]            s_axi_rresp,
    output wire [S_COUNT-1:0]              s_axi_rlast,
    output wire [S_COUNT*RUSER_WIDTH-1:0]  s_axi_ruser,
    output wire [S_COUNT-1:0]              s_axi_rvalid,
    input  wire [S_COUNT-1:0]              s_axi_rready,

    /*
     * AXI master interfaces
     */
    output wire [M_COUNT*ID_WIDTH-1:0]     m_axi_awid,
    output wire [M_COUNT*ADDR_WIDTH-1:0]   m_axi_awaddr,
    output wire [M_COUNT*8-1:0]            m_axi_awlen,
    output wire [M_COUNT*3-1:0]            m_axi_awsize,
    output wire [M_COUNT*2-1:0]            m_axi_awburst,
    output wire [M_COUNT-1:0]              m_axi_awlock,
    output wire [M_COUNT*4-1:0]            m_axi_awcache,
    output wire [M_COUNT*3-1:0]            m_axi_awprot,
    output wire [M_COUNT*4-1:0]            m_axi_awqos,
    output wire [M_COUNT*4-1:0]            m_axi_awregion,
    output wire [M_COUNT*AWUSER_WIDTH-1:0] m_axi_awuser,
    output wire [M_COUNT-1:0]              m_axi_awvalid,
    input  wire [M_COUNT-1:0]              m_axi_awready,
    output wire [M_COUNT*DATA_WIDTH-1:0]   m_axi_wdata,
    output wire [M_COUNT*STRB_WIDTH-1:0]   m_axi_wstrb,
    output wire [M_COUNT-1:0]              m_axi_wlast,
    output wire [M_COUNT*WUSER_WIDTH-1:0]  m_axi_wuser,
    output wire [M_COUNT-1:0]              m_axi_wvalid,
    input  wire [M_COUNT-1:0]              m_axi_wready,
    input  wire [M_COUNT*ID_WIDTH-1:0]     m_axi_bid,
    input  wire [M_COUNT*2-1:0]            m_axi_bresp,
    input  wire [M_COUNT*BUSER_WIDTH-1:0]  m_axi_buser,
    input  wire [M_COUNT-1:0]              m_axi_bvalid,
    output wire [M_COUNT-1:0]              m_axi_bready,
    output wire [M_COUNT*ID_WIDTH-1:0]     m_axi_arid,
    output wire [M_COUNT*ADDR_WIDTH-1:0]   m_axi_araddr,
    output wire [M_COUNT*8-1:0]            m_axi_arlen,
    output wire [M_COUNT*3-1:0]            m_axi_arsize,
    output wire [M_COUNT*2-1:0]            m_axi_arburst,
    output wire [M_COUNT-1:0]              m_axi_arlock,
    output wire [M_COUNT*4-1:0]            m_axi_arcache,
    output wire [M_COUNT*3-1:0]            m_axi_arprot,
    output wire [M_COUNT*4-1:0]            m_axi_arqos,
    output wire [M_COUNT*4-1:0]            m_axi_arregion,
    output wire [M_COUNT*ARUSER_WIDTH-1:0] m_axi_aruser,
    output wire [M_COUNT-1:0]              m_axi_arvalid,
    input  wire [M_COUNT-1:0]              m_axi_arready,
    input  wire [M_COUNT*ID_WIDTH-1:0]     m_axi_rid,
    input  wire [M_COUNT*DATA_WIDTH-1:0]   m_axi_rdata,
    input  wire [M_COUNT*2-1:0]            m_axi_rresp,
    input  wire [M_COUNT-1:0]              m_axi_rlast,
    input  wire [M_COUNT*RUSER_WIDTH-1:0]  m_axi_ruser,
    input  wire [M_COUNT-1:0]              m_axi_rvalid,
    output wire [M_COUNT-1:0]              m_axi_rready
);

parameter CL_S_COUNT = $clog2(S_COUNT);
parameter CL_M_COUNT = $clog2(M_COUNT);

parameter AUSER_WIDTH = AWUSER_WIDTH > ARUSER_WIDTH ? AWUSER_WIDTH : ARUSER_WIDTH;

// default address computation
function [M_COUNT*M_REGIONS*ADDR_WIDTH-1:0] calcBaseAddrs(input [31:0] dummy);
    integer i;
    reg [ADDR_WIDTH-1:0] base;
    begin
        calcBaseAddrs = {M_COUNT*M_REGIONS*ADDR_WIDTH{1'b0}};
        base = 0;
        for (i = 1; i < M_COUNT*M_REGIONS; i = i + 1) begin
            if (M_ADDR_WIDTH[i*32 +: 32]) begin
                base = base + 2**M_ADDR_WIDTH[(i-1)*32 +: 32]; // increment
                base = base - (base % 2**M_ADDR_WIDTH[i*32 +: 32]); // align
                calcBaseAddrs[i * ADDR_WIDTH +: ADDR_WIDTH] = base;
            end
        end
    end
endfunction

parameter M_BASE_ADDR_INT = M_BASE_ADDR ? M_BASE_ADDR : calcBaseAddrs(0);

integer i, j;

// check configuration
initial begin
    if (M_REGIONS < 1 || M_REGIONS > 16) begin
        $error("Error: M_REGIONS must be between 1 and 16 (instance %m)");
        $finish;
    end

    for (i = 0; i < M_COUNT*M_REGIONS; i = i + 1) begin
        if (M_ADDR_WIDTH[i*32 +: 32] && (M_ADDR_WIDTH[i*32 +: 32] < 12 || M_ADDR_WIDTH[i*32 +: 32] > ADDR_WIDTH)) begin
            $error("Error: address width out of range (instance %m)");
            $finish;
        end
    end

    $display("Addressing configuration for axi_interconnect instance %m");
    for (i = 0; i < M_COUNT*M_REGIONS; i = i + 1) begin
        if (M_ADDR_WIDTH[i*32 +: 32]) begin
            $display("%2d (%2d): %x / %2d -- %x-%x", i/M_REGIONS, i%M_REGIONS, M_BASE_ADDR_INT[i*ADDR_WIDTH +: ADDR_WIDTH], M_ADDR_WIDTH[i*32 +: 32], M_BASE_ADDR_INT[i*ADDR_WIDTH +: ADDR_WIDTH] & ({ADDR_WIDTH{1'b1}} << M_ADDR_WIDTH[i*32 +: 32]), M_BASE_ADDR_INT[i*ADDR_WIDTH +: ADDR_WIDTH] | ({ADDR_WIDTH{1'b1}} >> (ADDR_WIDTH - M_ADDR_WIDTH[i*32 +: 32])));
        end
    end

    for (i = 0; i < M_COUNT*M_REGIONS; i = i + 1) begin
        for (j = i+1; j < M_COUNT*M_REGIONS; j = j + 1) begin
            if (M_ADDR_WIDTH[i*32 +: 32] && M_ADDR_WIDTH[j*32 +: 32]) begin
                if (((M_BASE_ADDR_INT[i*ADDR_WIDTH +: ADDR_WIDTH] & ({ADDR_WIDTH{1'b1}} << M_ADDR_WIDTH[i*32 +: 32])) <= (M_BASE_ADDR_INT[j*ADDR_WIDTH +: ADDR_WIDTH] | ({ADDR_WIDTH{1'b1}} >> (ADDR_WIDTH - M_ADDR_WIDTH[j*32 +: 32])))) && ((M_BASE_ADDR_INT[j*ADDR_WIDTH +: ADDR_WIDTH] & ({ADDR_WIDTH{1'b1}} << M_ADDR_WIDTH[j*32 +: 32])) <= (M_BASE_ADDR_INT[i*ADDR_WIDTH +: ADDR_WIDTH] | ({ADDR_WIDTH{1'b1}} >> (ADDR_WIDTH - M_ADDR_WIDTH[i*32 +: 32]))))) begin
                    $display("Overlapping regions:");
                    $display("%2d (%2d): %x / %2d -- %x-%x", i/M_REGIONS, i%M_REGIONS, M_BASE_ADDR_INT[i*ADDR_WIDTH +: ADDR_WIDTH], M_ADDR_WIDTH[i*32 +: 32], M_BASE_ADDR_INT[i*ADDR_WIDTH +: ADDR_WIDTH] & ({ADDR_WIDTH{1'b1}} << M_ADDR_WIDTH[i*32 +: 32]), M_BASE_ADDR_INT[i*ADDR_WIDTH +: ADDR_WIDTH] | ({ADDR_WIDTH{1'b1}} >> (ADDR_WIDTH - M_ADDR_WIDTH[i*32 +: 32])));
                    $display("%2d (%2d): %x / %2d -- %x-%x", j/M_REGIONS, j%M_REGIONS, M_BASE_ADDR_INT[j*ADDR_WIDTH +: ADDR_WIDTH], M_ADDR_WIDTH[j*32 +: 32], M_BASE_ADDR_INT[j*ADDR_WIDTH +: ADDR_WIDTH] & ({ADDR_WIDTH{1'b1}} << M_ADDR_WIDTH[j*32 +: 32]), M_BASE_ADDR_INT[j*ADDR_WIDTH +: ADDR_WIDTH] | ({ADDR_WIDTH{1'b1}} >> (ADDR_WIDTH - M_ADDR_WIDTH[j*32 +: 32])));
                    $error("Error: address ranges overlap (instance %m)");
                    $finish;
                end
            end
        end
    end
end

localparam [2:0]
    STATE_IDLE = 3'd0,
    STATE_DECODE = 3'd1,
    STATE_WRITE = 3'd2,
    STATE_WRITE_RESP = 3'd3,
    STATE_WRITE_DROP = 3'd4,
    STATE_READ = 3'd5,
    STATE_READ_DROP = 3'd6,
    STATE_WAIT_IDLE = 3'd7;

reg [2:0] state_reg = STATE_IDLE, state_next;

reg match;

reg [CL_M_COUNT-1:0] m_select_reg = 2'd0, m_select_next;
reg [ID_WIDTH-1:0] axi_id_reg = {ID_WIDTH{1'b0}}, axi_id_next;
reg [ADDR_WIDTH-1:0] axi_addr_reg = {ADDR_WIDTH{1'b0}}, axi_addr_next;
reg axi_addr_valid_reg = 1'b0, axi_addr_valid_next;
reg [7:0] axi_len_reg = 8'd0, axi_len_next;
reg [2:0] axi_size_reg = 3'd0, axi_size_next;
reg [1:0] axi_burst_reg = 2'd0, axi_burst_next;
reg axi_lock_reg = 1'b0, axi_lock_next;
reg [3:0] axi_cache_reg = 4'd0, axi_cache_next;
reg [2:0] axi_prot_reg = 3'b000, axi_prot_next;
reg [3:0] axi_qos_reg = 4'd0, axi_qos_next;
reg [3:0] axi_region_reg = 4'd0, axi_region_next;
reg [AUSER_WIDTH-1:0] axi_auser_reg = {AUSER_WIDTH{1'b0}}, axi_auser_next;
reg [1:0] axi_bresp_reg = 2'b00, axi_bresp_next;
reg [BUSER_WIDTH-1:0] axi_buser_reg = {BUSER_WIDTH{1'b0}}, axi_buser_next;

reg [S_COUNT-1:0] s_axi_awready_reg = 0, s_axi_awready_next;
reg [S_COUNT-1:0] s_axi_wready_reg = 0, s_axi_wready_next;
reg [S_COUNT-1:0] s_axi_bvalid_reg = 0, s_axi_bvalid_next;
reg [S_COUNT-1:0] s_axi_arready_reg = 0, s_axi_arready_next;

reg [M_COUNT-1:0] m_axi_awvalid_reg = 0, m_axi_awvalid_next;
reg [M_COUNT-1:0] m_axi_bready_reg = 0, m_axi_bready_next;
reg [M_COUNT-1:0] m_axi_arvalid_reg = 0, m_axi_arvalid_next;
reg [M_COUNT-1:0] m_axi_rready_reg = 0, m_axi_rready_next;

// internal datapath
reg  [ID_WIDTH-1:0]    s_axi_rid_int;
reg  [DATA_WIDTH-1:0]  s_axi_rdata_int;
reg  [1:0]             s_axi_rresp_int;
reg                    s_axi_rlast_int;
reg  [RUSER_WIDTH-1:0] s_axi_ruser_int;
reg                    s_axi_rvalid_int;
reg                    s_axi_rready_int_reg = 1'b0;
wire                   s_axi_rready_int_early;

reg  [DATA_WIDTH-1:0]  m_axi_wdata_int;
reg  [STRB_WIDTH-1:0]  m_axi_wstrb_int;
reg                    m_axi_wlast_int;
reg  [WUSER_WIDTH-1:0] m_axi_wuser_int;
reg                    m_axi_wvalid_int;
reg                    m_axi_wready_int_reg = 1'b0;
wire                   m_axi_wready_int_early;

assign s_axi_awready = s_axi_awready_reg;
assign s_axi_wready = s_axi_wready_reg;
assign s_axi_bid = {S_COUNT{axi_id_reg}};
assign s_axi_bresp = {S_COUNT{axi_bresp_reg}};
assign s_axi_buser = {S_COUNT{BUSER_ENABLE ? axi_buser_reg : {BUSER_WIDTH{1'b0}}}};
assign s_axi_bvalid = s_axi_bvalid_reg;
assign s_axi_arready = s_axi_arready_reg;

assign m_axi_awid = {M_COUNT{FORWARD_ID ? axi_id_reg : {ID_WIDTH{1'b0}}}};
assign m_axi_awaddr = {M_COUNT{axi_addr_reg}};
assign m_axi_awlen = {M_COUNT{axi_len_reg}};
assign m_axi_awsize = {M_COUNT{axi_size_reg}};
assign m_axi_awburst = {M_COUNT{axi_burst_reg}};
assign m_axi_awlock = {M_COUNT{axi_lock_reg}};
assign m_axi_awcache = {M_COUNT{axi_cache_reg}};
assign m_axi_awprot = {M_COUNT{axi_prot_reg}};
assign m_axi_awqos = {M_COUNT{axi_qos_reg}};
assign m_axi_awregion = {M_COUNT{axi_region_reg}};
assign m_axi_awuser = {M_COUNT{AWUSER_ENABLE ? axi_auser_reg[AWUSER_WIDTH-1:0] : {AWUSER_WIDTH{1'b0}}}};
assign m_axi_awvalid = m_axi_awvalid_reg;
assign m_axi_bready = m_axi_bready_reg;
assign m_axi_arid = {M_COUNT{FORWARD_ID ? axi_id_reg : {ID_WIDTH{1'b0}}}};
assign m_axi_araddr = {M_COUNT{axi_addr_reg}};
assign m_axi_arlen = {M_COUNT{axi_len_reg}};
assign m_axi_arsize = {M_COUNT{axi_size_reg}};
assign m_axi_arburst = {M_COUNT{axi_burst_reg}};
assign m_axi_arlock = {M_COUNT{axi_lock_reg}};
assign m_axi_arcache = {M_COUNT{axi_cache_reg}};
assign m_axi_arprot = {M_COUNT{axi_prot_reg}};
assign m_axi_arqos = {M_COUNT{axi_qos_reg}};
assign m_axi_arregion = {M_COUNT{axi_region_reg}};
assign m_axi_aruser = {M_COUNT{ARUSER_ENABLE ? axi_auser_reg[ARUSER_WIDTH-1:0] : {ARUSER_WIDTH{1'b0}}}};
assign m_axi_arvalid = m_axi_arvalid_reg;
assign m_axi_rready = m_axi_rready_reg;

// slave side mux
wire [(CL_S_COUNT > 0 ? CL_S_COUNT-1 : 0):0] s_select;

wire [ID_WIDTH-1:0]     current_s_axi_awid      = s_axi_awid[s_select*ID_WIDTH +: ID_WIDTH];
wire [ADDR_WIDTH-1:0]   current_s_axi_awaddr    = s_axi_awaddr[s_select*ADDR_WIDTH +: ADDR_WIDTH];
wire [7:0]              current_s_axi_awlen     = s_axi_awlen[s_select*8 +: 8];
wire [2:0]              current_s_axi_awsize    = s_axi_awsize[s_select*3 +: 3];
wire [1:0]              current_s_axi_awburst   = s_axi_awburst[s_select*2 +: 2];
wire                    current_s_axi_awlock    = s_axi_awlock[s_select];
wire [3:0]              current_s_axi_awcache   = s_axi_awcache[s_select*4 +: 4];
wire [2:0]              current_s_axi_awprot    = s_axi_awprot[s_select*3 +: 3];
wire [3:0]              current_s_axi_awqos     = s_axi_awqos[s_select*4 +: 4];
wire [AWUSER_WIDTH-1:0] current_s_axi_awuser    = s_axi_awuser[s_select*AWUSER_WIDTH +: AWUSER_WIDTH];
wire                    current_s_axi_awvalid   = s_axi_awvalid[s_select];
wire                    current_s_axi_awready   = s_axi_awready[s_select];
wire [DATA_WIDTH-1:0]   current_s_axi_wdata     = s_axi_wdata[s_select*DATA_WIDTH +: DATA_WIDTH];
wire [STRB_WIDTH-1:0]   current_s_axi_wstrb     = s_axi_wstrb[s_select*STRB_WIDTH +: STRB_WIDTH];
wire                    current_s_axi_wlast     = s_axi_wlast[s_select];
wire [WUSER_WIDTH-1:0]  current_s_axi_wuser     = s_axi_wuser[s_select*WUSER_WIDTH +: WUSER_WIDTH];
wire                    current_s_axi_wvalid    = s_axi_wvalid[s_select];
wire                    current_s_axi_wready    = s_axi_wready[s_select];
wire [ID_WIDTH-1:0]     current_s_axi_bid       = s_axi_bid[s_select*ID_WIDTH +: ID_WIDTH];
wire [1:0]              current_s_axi_bresp     = s_axi_bresp[s_select*2 +: 2];
wire [BUSER_WIDTH-1:0]  current_s_axi_buser     = s_axi_buser[s_select*BUSER_WIDTH +: BUSER_WIDTH];
wire                    current_s_axi_bvalid    = s_axi_bvalid[s_select];
wire                    current_s_axi_bready    = s_axi_bready[s_select];
wire [ID_WIDTH-1:0]     current_s_axi_arid      = s_axi_arid[s_select*ID_WIDTH +: ID_WIDTH];
wire [ADDR_WIDTH-1:0]   current_s_axi_araddr    = s_axi_araddr[s_select*ADDR_WIDTH +: ADDR_WIDTH];
wire [7:0]              current_s_axi_arlen     = s_axi_arlen[s_select*8 +: 8];
wire [2:0]              current_s_axi_arsize    = s_axi_arsize[s_select*3 +: 3];
wire [1:0]              current_s_axi_arburst   = s_axi_arburst[s_select*2 +: 2];
wire                    current_s_axi_arlock    = s_axi_arlock[s_select];
wire [3:0]              current_s_axi_arcache   = s_axi_arcache[s_select*4 +: 4];
wire [2:0]              current_s_axi_arprot    = s_axi_arprot[s_select*3 +: 3];
wire [3:0]              current_s_axi_arqos     = s_axi_arqos[s_select*4 +: 4];
wire [ARUSER_WIDTH-1:0] current_s_axi_aruser    = s_axi_aruser[s_select*ARUSER_WIDTH +: ARUSER_WIDTH];
wire                    current_s_axi_arvalid   = s_axi_arvalid[s_select];
wire                    current_s_axi_arready   = s_axi_arready[s_select];
wire [ID_WIDTH-1:0]     current_s_axi_rid       = s_axi_rid[s_select*ID_WIDTH +: ID_WIDTH];
wire [DATA_WIDTH-1:0]   current_s_axi_rdata     = s_axi_rdata[s_select*DATA_WIDTH +: DATA_WIDTH];
wire [1:0]              current_s_axi_rresp     = s_axi_rresp[s_select*2 +: 2];
wire                    current_s_axi_rlast     = s_axi_rlast[s_select];
wire [RUSER_WIDTH-1:0]  current_s_axi_ruser     = s_axi_ruser[s_select*RUSER_WIDTH +: RUSER_WIDTH];
wire                    current_s_axi_rvalid    = s_axi_rvalid[s_select];
wire                    current_s_axi_rready    = s_axi_rready[s_select];

// master side mux
wire [ID_WIDTH-1:0]     current_m_axi_awid      = m_axi_awid[m_select_reg*ID_WIDTH +: ID_WIDTH];
wire [ADDR_WIDTH-1:0]   current_m_axi_awaddr    = m_axi_awaddr[m_select_reg*ADDR_WIDTH +: ADDR_WIDTH];
wire [7:0]              current_m_axi_awlen     = m_axi_awlen[m_select_reg*8 +: 8];
wire [2:0]              current_m_axi_awsize    = m_axi_awsize[m_select_reg*3 +: 3];
wire [1:0]              current_m_axi_awburst   = m_axi_awburst[m_select_reg*2 +: 2];
wire                    current_m_axi_awlock    = m_axi_awlock[m_select_reg];
wire [3:0]              current_m_axi_awcache   = m_axi_awcache[m_select_reg*4 +: 4];
wire [2:0]              current_m_axi_awprot    = m_axi_awprot[m_select_reg*3 +: 3];
wire [3:0]              current_m_axi_awqos     = m_axi_awqos[m_select_reg*4 +: 4];
wire [3:0]              current_m_axi_awregion  = m_axi_awregion[m_select_reg*4 +: 4];
wire [AWUSER_WIDTH-1:0] current_m_axi_awuser    = m_axi_awuser[m_select_reg*AWUSER_WIDTH +: AWUSER_WIDTH];
wire                    current_m_axi_awvalid   = m_axi_awvalid[m_select_reg];
wire                    current_m_axi_awready   = m_axi_awready[m_select_reg];
wire [DATA_WIDTH-1:0]   current_m_axi_wdata     = m_axi_wdata[m_select_reg*DATA_WIDTH +: DATA_WIDTH];
wire [STRB_WIDTH-1:0]   current_m_axi_wstrb     = m_axi_wstrb[m_select_reg*STRB_WIDTH +: STRB_WIDTH];
wire                    current_m_axi_wlast     = m_axi_wlast[m_select_reg];
wire [WUSER_WIDTH-1:0]  current_m_axi_wuser     = m_axi_wuser[m_select_reg*WUSER_WIDTH +: WUSER_WIDTH];
wire                    current_m_axi_wvalid    = m_axi_wvalid[m_select_reg];
wire                    current_m_axi_wready    = m_axi_wready[m_select_reg];
wire [ID_WIDTH-1:0]     current_m_axi_bid       = m_axi_bid[m_select_reg*ID_WIDTH +: ID_WIDTH];
wire [1:0]              current_m_axi_bresp     = m_axi_bresp[m_select_reg*2 +: 2];
wire [BUSER_WIDTH-1:0]  current_m_axi_buser     = m_axi_buser[m_select_reg*BUSER_WIDTH +: BUSER_WIDTH];
wire                    current_m_axi_bvalid    = m_axi_bvalid[m_select_reg];
wire                    current_m_axi_bready    = m_axi_bready[m_select_reg];
wire [ID_WIDTH-1:0]     current_m_axi_arid      = m_axi_arid[m_select_reg*ID_WIDTH +: ID_WIDTH];
wire [ADDR_WIDTH-1:0]   current_m_axi_araddr    = m_axi_araddr[m_select_reg*ADDR_WIDTH +: ADDR_WIDTH];
wire [7:0]              current_m_axi_arlen     = m_axi_arlen[m_select_reg*8 +: 8];
wire [2:0]              current_m_axi_arsize    = m_axi_arsize[m_select_reg*3 +: 3];
wire [1:0]              current_m_axi_arburst   = m_axi_arburst[m_select_reg*2 +: 2];
wire                    current_m_axi_arlock    = m_axi_arlock[m_select_reg];
wire [3:0]              current_m_axi_arcache   = m_axi_arcache[m_select_reg*4 +: 4];
wire [2:0]              current_m_axi_arprot    = m_axi_arprot[m_select_reg*3 +: 3];
wire [3:0]              current_m_axi_arqos     = m_axi_arqos[m_select_reg*4 +: 4];
wire [3:0]              current_m_axi_arregion  = m_axi_arregion[m_select_reg*4 +: 4];
wire [ARUSER_WIDTH-1:0] current_m_axi_aruser    = m_axi_aruser[m_select_reg*ARUSER_WIDTH +: ARUSER_WIDTH];
wire                    current_m_axi_arvalid   = m_axi_arvalid[m_select_reg];
wire                    current_m_axi_arready   = m_axi_arready[m_select_reg];
wire [ID_WIDTH-1:0]     current_m_axi_rid       = m_axi_rid[m_select_reg*ID_WIDTH +: ID_WIDTH];
wire [DATA_WIDTH-1:0]   current_m_axi_rdata     = m_axi_rdata[m_select_reg*DATA_WIDTH +: DATA_WIDTH];
wire [1:0]              current_m_axi_rresp     = m_axi_rresp[m_select_reg*2 +: 2];
wire                    current_m_axi_rlast     = m_axi_rlast[m_select_reg];
wire [RUSER_WIDTH-1:0]  current_m_axi_ruser     = m_axi_ruser[m_select_reg*RUSER_WIDTH +: RUSER_WIDTH];
wire                    current_m_axi_rvalid    = m_axi_rvalid[m_select_reg];
wire                    current_m_axi_rready    = m_axi_rready[m_select_reg];

// arbiter instance
wire [S_COUNT*2-1:0] request;
wire [S_COUNT*2-1:0] acknowledge;
wire [S_COUNT*2-1:0] grant;
wire grant_valid;
wire [CL_S_COUNT:0] grant_encoded;

wire read = grant_encoded[0];
assign s_select = grant_encoded >> 1;

arbiter #(
    .PORTS(S_COUNT*2),
    .TYPE("ROUND_ROBIN"),
    .BLOCK("ACKNOWLEDGE"),
    .LSB_PRIORITY("HIGH")
)
arb_inst (
    .clk(clk),
    .rst(rst),
    .request(request),
    .acknowledge(acknowledge),
    .grant(grant),
    .grant_valid(grant_valid),
    .grant_encoded(grant_encoded)
);

genvar n;

// request generation
generate
for (n = 0; n < S_COUNT; n = n + 1) begin
    assign request[2*n]   = s_axi_awvalid[n];
    assign request[2*n+1] = s_axi_arvalid[n];
end
endgenerate

// acknowledge generation
generate
for (n = 0; n < S_COUNT; n = n + 1) begin
    assign acknowledge[2*n]   = grant[2*n]   && s_axi_bvalid[n] && s_axi_bready[n];
    assign acknowledge[2*n+1] = grant[2*n+1] && s_axi_rvalid[n] && s_axi_rready[n] && s_axi_rlast[n];
end
endgenerate

always @* begin
    state_next = STATE_IDLE;

    match = 1'b0;

    m_select_next = m_select_reg;
    axi_id_next = axi_id_reg;
    axi_addr_next = axi_addr_reg;
    axi_addr_valid_next = axi_addr_valid_reg;
    axi_len_next = axi_len_reg;
    axi_size_next = axi_size_reg;
    axi_burst_next = axi_burst_reg;
    axi_lock_next = axi_lock_reg;
    axi_cache_next = axi_cache_reg;
    axi_prot_next = axi_prot_reg;
    axi_qos_next = axi_qos_reg;
    axi_region_next = axi_region_reg;
    axi_auser_next = axi_auser_reg;
    axi_bresp_next = axi_bresp_reg;
    axi_buser_next = axi_buser_reg;

    s_axi_awready_next = 0;
    s_axi_wready_next = 0;
    s_axi_bvalid_next = s_axi_bvalid_reg & ~s_axi_bready;
    s_axi_arready_next = 0;

    m_axi_awvalid_next = m_axi_awvalid_reg & ~m_axi_awready;
    m_axi_bready_next = 0;
    m_axi_arvalid_next = m_axi_arvalid_reg & ~m_axi_arready;
    m_axi_rready_next = 0;

    s_axi_rid_int = axi_id_reg;
    s_axi_rdata_int = current_m_axi_rdata;
    s_axi_rresp_int = current_m_axi_rresp;
    s_axi_rlast_int = current_m_axi_rlast;
    s_axi_ruser_int = current_m_axi_ruser;
    s_axi_rvalid_int = 1'b0;

    m_axi_wdata_int = current_s_axi_wdata;
    m_axi_wstrb_int = current_s_axi_wstrb;
    m_axi_wlast_int = current_s_axi_wlast;
    m_axi_wuser_int = current_s_axi_wuser;
    m_axi_wvalid_int = 1'b0;

    case (state_reg)
        STATE_IDLE: begin
            // idle state; wait for arbitration

            if (grant_valid) begin

                axi_addr_valid_next = 1'b1;

                if (read) begin
                    // reading
                    axi_addr_next = current_s_axi_araddr;
                    axi_prot_next = current_s_axi_arprot;
                    axi_id_next = current_s_axi_arid;
                    axi_addr_next = current_s_axi_araddr;
                    axi_len_next = current_s_axi_arlen;
                    axi_size_next = current_s_axi_arsize;
                    axi_burst_next = current_s_axi_arburst;
                    axi_lock_next = current_s_axi_arlock;
                    axi_cache_next = current_s_axi_arcache;
                    axi_prot_next = current_s_axi_arprot;
                    axi_qos_next = current_s_axi_arqos;
                    axi_auser_next = current_s_axi_aruser;
                    s_axi_arready_next[s_select] = 1'b1;
                end else  begin
                    // writing
                    axi_addr_next = current_s_axi_awaddr;
                    axi_prot_next = current_s_axi_awprot;
                    axi_id_next = current_s_axi_awid;
                    axi_addr_next = current_s_axi_awaddr;
                    axi_len_next = current_s_axi_awlen;
                    axi_size_next = current_s_axi_awsize;
                    axi_burst_next = current_s_axi_awburst;
                    axi_lock_next = current_s_axi_awlock;
                    axi_cache_next = current_s_axi_awcache;
                    axi_prot_next = current_s_axi_awprot;
                    axi_qos_next = current_s_axi_awqos;
                    axi_auser_next = current_s_axi_awuser;
                    s_axi_awready_next[s_select] = 1'b1;
                end

                state_next = STATE_DECODE;
            end else begin
                state_next = STATE_IDLE;
            end
        end
        STATE_DECODE: begin
            // decode state; determine master interface

            match = 1'b0;
            for (i = 0; i < M_COUNT; i = i + 1) begin
                for (j = 0; j < M_REGIONS; j = j + 1) begin
                    if (M_ADDR_WIDTH[(i*M_REGIONS+j)*32 +: 32] && (!M_SECURE[i] || !axi_prot_reg[1]) && ((read ? M_CONNECT_READ : M_CONNECT_WRITE) & (1 << (s_select+i*S_COUNT))) && (axi_addr_reg >> M_ADDR_WIDTH[(i*M_REGIONS+j)*32 +: 32]) == (M_BASE_ADDR_INT[(i*M_REGIONS+j)*ADDR_WIDTH +: ADDR_WIDTH] >> M_ADDR_WIDTH[(i*M_REGIONS+j)*32 +: 32])) begin
                        m_select_next = i;
                        axi_region_next = j;
                        match = 1'b1;
                    end
                end
            end

            if (match) begin
                if (read) begin
                    // reading
                    m_axi_rready_next[m_select_reg] = s_axi_rready_int_early;
                    state_next = STATE_READ;
                end else begin
                    // writing
                    s_axi_wready_next[s_select] = m_axi_wready_int_early;
                    state_next = STATE_WRITE;
                end
            end else begin
                // no match; return decode error
                if (read) begin
                    // reading
                    state_next = STATE_READ_DROP;
                end else begin
                    // writing
                    axi_bresp_next = 2'b11;
                    s_axi_wready_next[s_select] = 1'b1;
                    state_next = STATE_WRITE_DROP;
                end
            end
        end
        STATE_WRITE: begin
            // write state; store and forward write data
            s_axi_wready_next[s_select] = m_axi_wready_int_early;

            if (axi_addr_valid_reg) begin
                m_axi_awvalid_next[m_select_reg] = 1'b1;
            end
            axi_addr_valid_next = 1'b0;

            if (current_s_axi_wready && current_s_axi_wvalid) begin
                m_axi_wdata_int = current_s_axi_wdata;
                m_axi_wstrb_int = current_s_axi_wstrb;
                m_axi_wlast_int = current_s_axi_wlast;
                m_axi_wuser_int = current_s_axi_wuser;
                m_axi_wvalid_int = 1'b1;

                if (current_s_axi_wlast) begin
                    s_axi_wready_next[s_select] = 1'b0;
                    m_axi_bready_next[m_select_reg] = 1'b1;
                    state_next = STATE_WRITE_RESP;
                end else begin
                    state_next = STATE_WRITE;
                end
            end else begin
                state_next = STATE_WRITE;
            end
        end
        STATE_WRITE_RESP: begin
            // write response state; store and forward write response
            m_axi_bready_next[m_select_reg] = 1'b1;

            if (current_m_axi_bready && current_m_axi_bvalid) begin
                m_axi_bready_next[m_select_reg] = 1'b0;
                axi_bresp_next = current_m_axi_bresp;
                s_axi_bvalid_next[s_select] = 1'b1;
                state_next = STATE_WAIT_IDLE;
            end else begin
                state_next = STATE_WRITE_RESP;
            end
        end
        STATE_WRITE_DROP: begin
            // write drop state; drop write data
            s_axi_wready_next[s_select] = 1'b1;

            axi_addr_valid_next = 1'b0;

            if (current_s_axi_wready && current_s_axi_wvalid && current_s_axi_wlast) begin
                s_axi_wready_next[s_select] = 1'b0;
                s_axi_bvalid_next[s_select] = 1'b1;
                state_next = STATE_WAIT_IDLE;
            end else begin
                state_next = STATE_WRITE_DROP;
            end
        end
        STATE_READ: begin
            // read state; store and forward read response
            m_axi_rready_next[m_select_reg] = s_axi_rready_int_early;

            if (axi_addr_valid_reg) begin
                m_axi_arvalid_next[m_select_reg] = 1'b1;
            end
            axi_addr_valid_next = 1'b0;

            if (current_m_axi_rready && current_m_axi_rvalid) begin
                s_axi_rid_int = axi_id_reg;
                s_axi_rdata_int = current_m_axi_rdata;
                s_axi_rresp_int = current_m_axi_rresp;
                s_axi_rlast_int = current_m_axi_rlast;
                s_axi_ruser_int = current_m_axi_ruser;
                s_axi_rvalid_int = 1'b1;

                if (current_m_axi_rlast) begin
                    m_axi_rready_next[m_select_reg] = 1'b0;
                    state_next = STATE_WAIT_IDLE;
                end else begin
                    state_next = STATE_READ;
                end
            end else begin
                state_next = STATE_READ;
            end
        end
        STATE_READ_DROP: begin
            // read drop state; generate decode error read response

            s_axi_rid_int = axi_id_reg;
            s_axi_rdata_int = {DATA_WIDTH{1'b0}};
            s_axi_rresp_int = 2'b11;
            s_axi_rlast_int = axi_len_reg == 0;
            s_axi_ruser_int = {RUSER_WIDTH{1'b0}};
            s_axi_rvalid_int = 1'b1;

            if (s_axi_rready_int_reg) begin
                axi_len_next = axi_len_reg - 1;
                if (axi_len_reg == 0) begin
                    state_next = STATE_WAIT_IDLE;
                end else begin
                    state_next = STATE_READ_DROP;
                end
            end else begin
                state_next = STATE_READ_DROP;
            end
        end
        STATE_WAIT_IDLE: begin
            // wait for idle state; wait untl grant valid is deasserted

            if (!grant_valid || acknowledge) begin
                state_next = STATE_IDLE;
            end else begin
                state_next = STATE_WAIT_IDLE;
            end
        end
    endcase
end

always @(posedge clk) begin
    if (rst) begin
        state_reg <= STATE_IDLE;

        s_axi_awready_reg <= 0;
        s_axi_wready_reg <= 0;
        s_axi_bvalid_reg <= 0;
        s_axi_arready_reg <= 0;

        m_axi_awvalid_reg <= 0;
        m_axi_bready_reg <= 0;
        m_axi_arvalid_reg <= 0;
        m_axi_rready_reg <= 0;
    end else begin
        state_reg <= state_next;

        s_axi_awready_reg <= s_axi_awready_next;
        s_axi_wready_reg <= s_axi_wready_next;
        s_axi_bvalid_reg <= s_axi_bvalid_next;
        s_axi_arready_reg <= s_axi_arready_next;

        m_axi_awvalid_reg <= m_axi_awvalid_next;
        m_axi_bready_reg <= m_axi_bready_next;
        m_axi_arvalid_reg <= m_axi_arvalid_next;
        m_axi_rready_reg <= m_axi_rready_next;
    end

    m_select_reg <= m_select_next;
    axi_id_reg <= axi_id_next;
    axi_addr_reg <= axi_addr_next;
    axi_addr_valid_reg <= axi_addr_valid_next;
    axi_len_reg <= axi_len_next;
    axi_size_reg <= axi_size_next;
    axi_burst_reg <= axi_burst_next;
    axi_lock_reg <= axi_lock_next;
    axi_cache_reg <= axi_cache_next;
    axi_prot_reg <= axi_prot_next;
    axi_qos_reg <= axi_qos_next;
    axi_region_reg <= axi_region_next;
    axi_auser_reg <= axi_auser_next;
    axi_bresp_reg <= axi_bresp_next;
    axi_buser_reg <= axi_buser_next;
end

// output datapath logic (R channel)
reg [ID_WIDTH-1:0]    s_axi_rid_reg    = {ID_WIDTH{1'b0}};
reg [DATA_WIDTH-1:0]  s_axi_rdata_reg  = {DATA_WIDTH{1'b0}};
reg [1:0]             s_axi_rresp_reg  = 2'd0;
reg                   s_axi_rlast_reg  = 1'b0;
reg [RUSER_WIDTH-1:0] s_axi_ruser_reg  = 1'b0;
reg [S_COUNT-1:0]     s_axi_rvalid_reg = 1'b0, s_axi_rvalid_next;

reg [ID_WIDTH-1:0]    temp_s_axi_rid_reg    = {ID_WIDTH{1'b0}};
reg [DATA_WIDTH-1:0]  temp_s_axi_rdata_reg  = {DATA_WIDTH{1'b0}};
reg [1:0]             temp_s_axi_rresp_reg  = 2'd0;
reg                   temp_s_axi_rlast_reg  = 1'b0;
reg [RUSER_WIDTH-1:0] temp_s_axi_ruser_reg  = 1'b0;
reg                   temp_s_axi_rvalid_reg = 1'b0, temp_s_axi_rvalid_next;

// datapath control
reg store_axi_r_int_to_output;
reg store_axi_r_int_to_temp;
reg store_axi_r_temp_to_output;

assign s_axi_rid = {S_COUNT{s_axi_rid_reg}};
assign s_axi_rdata = {S_COUNT{s_axi_rdata_reg}};
assign s_axi_rresp = {S_COUNT{s_axi_rresp_reg}};
assign s_axi_rlast = {S_COUNT{s_axi_rlast_reg}};
assign s_axi_ruser = {S_COUNT{RUSER_ENABLE ? s_axi_ruser_reg : {RUSER_WIDTH{1'b0}}}};
assign s_axi_rvalid = s_axi_rvalid_reg;

// enable ready input next cycle if output is ready or the temp reg will not be filled on the next cycle (output reg empty or no input)
assign s_axi_rready_int_early = current_s_axi_rready | (~temp_s_axi_rvalid_reg & (~current_s_axi_rvalid | ~s_axi_rvalid_int));

always @* begin
    // transfer sink ready state to source
    s_axi_rvalid_next = s_axi_rvalid_reg;
    temp_s_axi_rvalid_next = temp_s_axi_rvalid_reg;

    store_axi_r_int_to_output = 1'b0;
    store_axi_r_int_to_temp = 1'b0;
    store_axi_r_temp_to_output = 1'b0;

    if (s_axi_rready_int_reg) begin
        // input is ready
        if (current_s_axi_rready | ~current_s_axi_rvalid) begin
            // output is ready or currently not valid, transfer data to output
            s_axi_rvalid_next[s_select] = s_axi_rvalid_int;
            store_axi_r_int_to_output = 1'b1;
        end else begin
            // output is not ready, store input in temp
            temp_s_axi_rvalid_next = s_axi_rvalid_int;
            store_axi_r_int_to_temp = 1'b1;
        end
    end else if (current_s_axi_rready) begin
        // input is not ready, but output is ready
        s_axi_rvalid_next[s_select] = temp_s_axi_rvalid_reg;
        temp_s_axi_rvalid_next = 1'b0;
        store_axi_r_temp_to_output = 1'b1;
    end
end

always @(posedge clk) begin
    if (rst) begin
        s_axi_rvalid_reg <= 1'b0;
        s_axi_rready_int_reg <= 1'b0;
        temp_s_axi_rvalid_reg <= 1'b0;
    end else begin
        s_axi_rvalid_reg <= s_axi_rvalid_next;
        s_axi_rready_int_reg <= s_axi_rready_int_early;
        temp_s_axi_rvalid_reg <= temp_s_axi_rvalid_next;
    end

    // datapath
    if (store_axi_r_int_to_output) begin
        s_axi_rid_reg <= s_axi_rid_int;
        s_axi_rdata_reg <= s_axi_rdata_int;
        s_axi_rresp_reg <= s_axi_rresp_int;
        s_axi_rlast_reg <= s_axi_rlast_int;
        s_axi_ruser_reg <= s_axi_ruser_int;
    end else if (store_axi_r_temp_to_output) begin
        s_axi_rid_reg <= temp_s_axi_rid_reg;
        s_axi_rdata_reg <= temp_s_axi_rdata_reg;
        s_axi_rresp_reg <= temp_s_axi_rresp_reg;
        s_axi_rlast_reg <= temp_s_axi_rlast_reg;
        s_axi_ruser_reg <= temp_s_axi_ruser_reg;
    end

    if (store_axi_r_int_to_temp) begin
        temp_s_axi_rid_reg <= s_axi_rid_int;
        temp_s_axi_rdata_reg <= s_axi_rdata_int;
        temp_s_axi_rresp_reg <= s_axi_rresp_int;
        temp_s_axi_rlast_reg <= s_axi_rlast_int;
        temp_s_axi_ruser_reg <= s_axi_ruser_int;
    end
end

// output datapath logic (W channel)
reg [DATA_WIDTH-1:0]  m_axi_wdata_reg  = {DATA_WIDTH{1'b0}};
reg [STRB_WIDTH-1:0]  m_axi_wstrb_reg  = {STRB_WIDTH{1'b0}};
reg                   m_axi_wlast_reg  = 1'b0;
reg [WUSER_WIDTH-1:0] m_axi_wuser_reg  = 1'b0;
reg [M_COUNT-1:0]     m_axi_wvalid_reg = 1'b0, m_axi_wvalid_next;

reg [DATA_WIDTH-1:0]  temp_m_axi_wdata_reg  = {DATA_WIDTH{1'b0}};
reg [STRB_WIDTH-1:0]  temp_m_axi_wstrb_reg  = {STRB_WIDTH{1'b0}};
reg                   temp_m_axi_wlast_reg  = 1'b0;
reg [WUSER_WIDTH-1:0] temp_m_axi_wuser_reg  = 1'b0;
reg                   temp_m_axi_wvalid_reg = 1'b0, temp_m_axi_wvalid_next;

// datapath control
reg store_axi_w_int_to_output;
reg store_axi_w_int_to_temp;
reg store_axi_w_temp_to_output;

assign m_axi_wdata = {M_COUNT{m_axi_wdata_reg}};
assign m_axi_wstrb = {M_COUNT{m_axi_wstrb_reg}};
assign m_axi_wlast = {M_COUNT{m_axi_wlast_reg}};
assign m_axi_wuser = {M_COUNT{WUSER_ENABLE ? m_axi_wuser_reg : {WUSER_WIDTH{1'b0}}}};
assign m_axi_wvalid = m_axi_wvalid_reg;

// enable ready input next cycle if output is ready or the temp reg will not be filled on the next cycle (output reg empty or no input)
assign m_axi_wready_int_early = current_m_axi_wready | (~temp_m_axi_wvalid_reg & (~current_m_axi_wvalid | ~m_axi_wvalid_int));

always @* begin
    // transfer sink ready state to source
    m_axi_wvalid_next = m_axi_wvalid_reg;
    temp_m_axi_wvalid_next = temp_m_axi_wvalid_reg;

    store_axi_w_int_to_output = 1'b0;
    store_axi_w_int_to_temp = 1'b0;
    store_axi_w_temp_to_output = 1'b0;

    if (m_axi_wready_int_reg) begin
        // input is ready
        if (current_m_axi_wready | ~current_m_axi_wvalid) begin
            // output is ready or currently not valid, transfer data to output
            m_axi_wvalid_next[m_select_reg] = m_axi_wvalid_int;
            store_axi_w_int_to_output = 1'b1;
        end else begin
            // output is not ready, store input in temp
            temp_m_axi_wvalid_next = m_axi_wvalid_int;
            store_axi_w_int_to_temp = 1'b1;
        end
    end else if (current_m_axi_wready) begin
        // input is not ready, but output is ready
        m_axi_wvalid_next[m_select_reg] = temp_m_axi_wvalid_reg;
        temp_m_axi_wvalid_next = 1'b0;
        store_axi_w_temp_to_output = 1'b1;
    end
end

always @(posedge clk) begin
    if (rst) begin
        m_axi_wvalid_reg <= 1'b0;
        m_axi_wready_int_reg <= 1'b0;
        temp_m_axi_wvalid_reg <= 1'b0;
    end else begin
        m_axi_wvalid_reg <= m_axi_wvalid_next;
        m_axi_wready_int_reg <= m_axi_wready_int_early;
        temp_m_axi_wvalid_reg <= temp_m_axi_wvalid_next;
    end

    // datapath
    if (store_axi_w_int_to_output) begin
        m_axi_wdata_reg <= m_axi_wdata_int;
        m_axi_wstrb_reg <= m_axi_wstrb_int;
        m_axi_wlast_reg <= m_axi_wlast_int;
        m_axi_wuser_reg <= m_axi_wuser_int;
    end else if (store_axi_w_temp_to_output) begin
        m_axi_wdata_reg <= temp_m_axi_wdata_reg;
        m_axi_wstrb_reg <= temp_m_axi_wstrb_reg;
        m_axi_wlast_reg <= temp_m_axi_wlast_reg;
        m_axi_wuser_reg <= temp_m_axi_wuser_reg;
    end

    if (store_axi_w_int_to_temp) begin
        temp_m_axi_wdata_reg <= m_axi_wdata_int;
        temp_m_axi_wstrb_reg <= m_axi_wstrb_int;
        temp_m_axi_wlast_reg <= m_axi_wlast_int;
        temp_m_axi_wuser_reg <= m_axi_wuser_int;
    end
end

endmodule
