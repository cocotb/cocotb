/*
 * Copyright cocotb contributors
 * Licensed under the Revised BSD License, see LICENSE for details.
 * SPDX-License-Identifier: BSD-3-Clause
 */

// Language: Verilog 2001

`timescale 1ns / 1ps

/*
 * AXI4 ram and interconnect
 */

 module top #
 (
    // Width of data bus in bits
    parameter DATA_WIDTH = 32,
    // Width of address bus in bits
    parameter ADDR_WIDTH = 32,
    // Width of wstrb (width of data bus in words)
    parameter STRB_WIDTH = (DATA_WIDTH/8),
    // Width of ID signal
    parameter ID_WIDTH = 8,
    // Width of awuser signal
    parameter AWUSER_WIDTH = 8,
    // Width of wuser signal
    parameter WUSER_WIDTH = 8,
    // Width of buser signal
    parameter BUSER_WIDTH = 8,
    // Width of aruser signal
    parameter ARUSER_WIDTH = 8,
    // Width of ruser signal
    parameter RUSER_WIDTH = 8,
    // Base RAM address
    parameter RAM_BASE_ADDRESS = 32'h4000,
    // RAM width (RAM size = 2^RAM_WIDTH)
    parameter RAM_WIDTH = 13,
    // Extra pipeline register on RAM output
    parameter RAM_PIPELINE_OUTPUT = 1,
    // AW channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter AW_REG_TYPE = 2,
    // W channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter W_REG_TYPE = 0,
    // B channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter B_REG_TYPE = 1,
    // AR channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter AR_REG_TYPE = 2,
    // R channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter R_REG_TYPE = 0
 )
 (
    input  wire                   clk,
    input  wire                   rstn,

    input  wire [ID_WIDTH-1:0]    S_AXI_AWID,
    input  wire [ADDR_WIDTH-1:0]  S_AXI_AWADDR,
    input  wire [7:0]             S_AXI_AWLEN,
    input  wire [2:0]             S_AXI_AWSIZE,
    input  wire [1:0]             S_AXI_AWBURST,
    input  wire                   S_AXI_AWLOCK,
    input  wire [3:0]             S_AXI_AWCACHE,
    input  wire [2:0]             S_AXI_AWPROT,
    input  wire [3:0]             S_AXI_AWQOS,
    input  wire [AWUSER_WIDTH-1:0] S_AXI_AWUSER,
    input  wire                   S_AXI_AWVALID,
    output wire                   S_AXI_AWREADY,
    input  wire [DATA_WIDTH-1:0]  S_AXI_WDATA,
    input  wire [STRB_WIDTH-1:0]  S_AXI_WSTRB,
    input  wire                   S_AXI_WLAST,
    input  wire [WUSER_WIDTH-1:0] S_AXI_WUSER,
    input  wire                   S_AXI_WVALID,
    output wire                   S_AXI_WREADY,
    output wire [ID_WIDTH-1:0]    S_AXI_BID,
    output wire [1:0]             S_AXI_BRESP,
    output wire [BUSER_WIDTH-1:0] S_AXI_BUSER,
    output wire                   S_AXI_BVALID,
    input  wire                   S_AXI_BREADY,
    input  wire [ID_WIDTH-1:0]    S_AXI_ARID,
    input  wire [ADDR_WIDTH-1:0]  S_AXI_ARADDR,
    input  wire [7:0]             S_AXI_ARLEN,
    input  wire [2:0]             S_AXI_ARSIZE,
    input  wire [1:0]             S_AXI_ARBURST,
    input  wire                   S_AXI_ARLOCK,
    input  wire [3:0]             S_AXI_ARCACHE,
    input  wire [2:0]             S_AXI_ARPROT,
    input  wire [3:0]             S_AXI_ARQOS,
    input  wire [ARUSER_WIDTH-1:0] S_AXI_ARUSER,
    input  wire                   S_AXI_ARVALID,
    output wire                   S_AXI_ARREADY,
    output wire [ID_WIDTH-1:0]    S_AXI_RID,
    output wire [DATA_WIDTH-1:0]  S_AXI_RDATA,
    output wire [1:0]             S_AXI_RRESP,
    output wire                   S_AXI_RLAST,
    output wire [RUSER_WIDTH-1:0] S_AXI_RUSER,
    output wire                   S_AXI_RVALID,
    input  wire                   S_AXI_RREADY
);

wire [ID_WIDTH-1:0]     reg_axi_awid;
wire [ADDR_WIDTH-1:0]   reg_axi_awaddr;
wire [7:0]              reg_axi_awlen;
wire [2:0]              reg_axi_awsize;
wire [1:0]              reg_axi_awburst;
wire                    reg_axi_awlock;
wire [3:0]              reg_axi_awcache;
wire [2:0]              reg_axi_awprot;
wire [3:0]              reg_axi_awqos;
wire [3:0]              reg_axi_awregion;
wire [AWUSER_WIDTH-1:0] reg_axi_awuser;
wire                    reg_axi_awvalid;
wire                    reg_axi_awready;
wire [DATA_WIDTH-1:0]   reg_axi_wdata;
wire [STRB_WIDTH-1:0]   reg_axi_wstrb;
wire                    reg_axi_wlast;
wire [WUSER_WIDTH-1:0]  reg_axi_wuser;
wire                    reg_axi_wvalid;
wire                    reg_axi_wready;
wire [ID_WIDTH-1:0]     reg_axi_bid;
wire [1:0]              reg_axi_bresp;
wire [BUSER_WIDTH-1:0]  reg_axi_buser;
wire                    reg_axi_bvalid;
wire                    reg_axi_bready;
wire [ID_WIDTH-1:0]     reg_axi_arid;
wire [ADDR_WIDTH-1:0]   reg_axi_araddr;
wire [7:0]              reg_axi_arlen;
wire [2:0]              reg_axi_arsize;
wire [1:0]              reg_axi_arburst;
wire                    reg_axi_arlock;
wire [3:0]              reg_axi_arcache;
wire [2:0]              reg_axi_arprot;
wire [3:0]              reg_axi_arqos;
wire [3:0]              reg_axi_arregion;
wire [ARUSER_WIDTH-1:0] reg_axi_aruser;
wire                    reg_axi_arvalid;
wire                    reg_axi_arready;
wire [ID_WIDTH-1:0]     reg_axi_rid;
wire [DATA_WIDTH-1:0]   reg_axi_rdata;
wire [1:0]              reg_axi_rresp;
wire                    reg_axi_rlast;
wire [RUSER_WIDTH-1:0]  reg_axi_ruser;
wire                    reg_axi_rvalid;
wire                    reg_axi_rready;

wire [ID_WIDTH-1:0]    int_axi_awid;
wire [ADDR_WIDTH-1:0]  int_axi_awaddr;
wire [7:0]             int_axi_awlen;
wire [2:0]             int_axi_awsize;
wire [1:0]             int_axi_awburst;
wire                   int_axi_awlock;
wire [3:0]             int_axi_awcache;
wire [2:0]             int_axi_awprot;
wire [3:0]             int_axi_awregion;
wire                   int_axi_awvalid;
wire                   int_axi_awready;
wire [DATA_WIDTH-1:0]  int_axi_wdata;
wire [STRB_WIDTH-1:0]  int_axi_wstrb;
wire                   int_axi_wlast;
wire                   int_axi_wvalid;
wire                   int_axi_wready;
wire [ID_WIDTH-1:0]    int_axi_bid;
wire [1:0]             int_axi_bresp;
wire                   int_axi_bvalid;
wire                   int_axi_bready;
wire [ID_WIDTH-1:0]    int_axi_arid;
wire [ADDR_WIDTH-1:0]  int_axi_araddr;
wire [7:0]             int_axi_arlen;
wire [2:0]             int_axi_arsize;
wire [1:0]             int_axi_arburst;
wire                   int_axi_arlock;
wire [3:0]             int_axi_arcache;
wire [2:0]             int_axi_arprot;
wire [3:0]             int_axi_arregion;
wire                   int_axi_arvalid;
wire                   int_axi_arready;
wire [ID_WIDTH-1:0]    int_axi_rid;
wire [DATA_WIDTH-1:0]  int_axi_rdata;
wire [1:0]             int_axi_rresp;
wire                   int_axi_rlast;
wire                   int_axi_rvalid;
wire                   int_axi_rready;

axi_register #
(
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(ADDR_WIDTH),
    .STRB_WIDTH(STRB_WIDTH),
    .ID_WIDTH(ID_WIDTH),
    .AWUSER_ENABLE(1),
    .AWUSER_WIDTH(AWUSER_WIDTH),
    .WUSER_ENABLE(1),
    .WUSER_WIDTH(WUSER_WIDTH),
    .BUSER_ENABLE(1),
    .BUSER_WIDTH(BUSER_WIDTH),
    .ARUSER_ENABLE(1),
    .ARUSER_WIDTH(ARUSER_WIDTH),
    .RUSER_ENABLE(1),
    .RUSER_WIDTH(RUSER_WIDTH),
    .AW_REG_TYPE(AW_REG_TYPE),
    .W_REG_TYPE(W_REG_TYPE),
    .B_REG_TYPE(B_REG_TYPE),
    .AR_REG_TYPE(AR_REG_TYPE),
    .R_REG_TYPE(R_REG_TYPE)
)
axi_register_inst (
    .clk(clk),
    .rst(~rstn),

    .s_axi_awid(S_AXI_AWID),
    .s_axi_awaddr(S_AXI_AWADDR),
    .s_axi_awlen(S_AXI_AWLEN),
    .s_axi_awsize(S_AXI_AWSIZE),
    .s_axi_awburst(S_AXI_AWBURST),
    .s_axi_awlock(S_AXI_AWLOCK),
    .s_axi_awcache(S_AXI_AWCACHE),
    .s_axi_awprot(S_AXI_AWPROT),
    .s_axi_awqos(S_AXI_AWQOS),
    .s_axi_awuser(S_AXI_AWUSER),
    .s_axi_awvalid(S_AXI_AWVALID),
    .s_axi_awready(S_AXI_AWREADY),
    .s_axi_wdata(S_AXI_WDATA),
    .s_axi_wstrb(S_AXI_WSTRB),
    .s_axi_wlast(S_AXI_WLAST),
    .s_axi_wuser(S_AXI_WUSER),
    .s_axi_wvalid(S_AXI_WVALID),
    .s_axi_wready(S_AXI_WREADY),
    .s_axi_bid(S_AXI_BID),
    .s_axi_bresp(S_AXI_BRESP),
    .s_axi_buser(S_AXI_BUSER),
    .s_axi_bvalid(S_AXI_BVALID),
    .s_axi_bready(S_AXI_BREADY),
    .s_axi_arid(S_AXI_ARID),
    .s_axi_araddr(S_AXI_ARADDR),
    .s_axi_arlen(S_AXI_ARLEN),
    .s_axi_arsize(S_AXI_ARSIZE),
    .s_axi_arburst(S_AXI_ARBURST),
    .s_axi_arlock(S_AXI_ARLOCK),
    .s_axi_arcache(S_AXI_ARCACHE),
    .s_axi_arprot(S_AXI_ARPROT),
    .s_axi_arqos(S_AXI_ARQOS),
    .s_axi_aruser(S_AXI_ARUSER),
    .s_axi_arvalid(S_AXI_ARVALID),
    .s_axi_arready(S_AXI_ARREADY),
    .s_axi_rid(S_AXI_RID),
    .s_axi_rdata(S_AXI_RDATA),
    .s_axi_rresp(S_AXI_RRESP),
    .s_axi_rlast(S_AXI_RLAST),
    .s_axi_ruser(S_AXI_RUSER),
    .s_axi_rvalid(S_AXI_RVALID),
    .s_axi_rready(S_AXI_RREADY),

    .m_axi_awid(reg_axi_awid),
    .m_axi_awaddr(reg_axi_awaddr),
    .m_axi_awlen(reg_axi_awlen),
    .m_axi_awsize(reg_axi_awsize),
    .m_axi_awburst(reg_axi_awburst),
    .m_axi_awlock(reg_axi_awlock),
    .m_axi_awcache(reg_axi_awcache),
    .m_axi_awprot(reg_axi_awprot),
    .m_axi_awqos(reg_axi_awqos),
    .m_axi_awuser(reg_axi_awuser),
    .m_axi_awvalid(reg_axi_awvalid),
    .m_axi_awready(reg_axi_awready),
    .m_axi_wdata(reg_axi_wdata),
    .m_axi_wstrb(reg_axi_wstrb),
    .m_axi_wlast(reg_axi_wlast),
    .m_axi_wuser(reg_axi_wuser),
    .m_axi_wvalid(reg_axi_wvalid),
    .m_axi_wready(reg_axi_wready),
    .m_axi_bid(reg_axi_bid),
    .m_axi_bresp(reg_axi_bresp),
    .m_axi_buser(reg_axi_buser),
    .m_axi_bvalid(reg_axi_bvalid),
    .m_axi_bready(reg_axi_bready),
    .m_axi_arid(reg_axi_arid),
    .m_axi_araddr(reg_axi_araddr),
    .m_axi_arlen(reg_axi_arlen),
    .m_axi_arsize(reg_axi_arsize),
    .m_axi_arburst(reg_axi_arburst),
    .m_axi_arlock(reg_axi_arlock),
    .m_axi_arcache(reg_axi_arcache),
    .m_axi_arprot(reg_axi_arprot),
    .m_axi_arqos(reg_axi_arqos),
    .m_axi_aruser(reg_axi_aruser),
    .m_axi_arvalid(reg_axi_arvalid),
    .m_axi_arready(reg_axi_arready),
    .m_axi_rid(reg_axi_rid),
    .m_axi_rdata(reg_axi_rdata),
    .m_axi_rresp(reg_axi_rresp),
    .m_axi_rlast(reg_axi_rlast),
    .m_axi_ruser(reg_axi_ruser),
    .m_axi_rvalid(reg_axi_rvalid),
    .m_axi_rready(reg_axi_rready)
);

axi_interconnect #(
    .S_COUNT(1),
    .M_COUNT(1),
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(ADDR_WIDTH),
    .STRB_WIDTH(STRB_WIDTH),
    .ID_WIDTH(ID_WIDTH),
    .AWUSER_ENABLE(1),
    .AWUSER_WIDTH(AWUSER_WIDTH),
    .WUSER_ENABLE(1),
    .WUSER_WIDTH(WUSER_WIDTH),
    .BUSER_ENABLE(1),
    .BUSER_WIDTH(BUSER_WIDTH),
    .ARUSER_ENABLE(1),
    .ARUSER_WIDTH(ARUSER_WIDTH),
    .RUSER_ENABLE(1),
    .RUSER_WIDTH(RUSER_WIDTH),
    .FORWARD_ID(1),
    .M_REGIONS(1),
    .M_BASE_ADDR({RAM_BASE_ADDRESS}),
    .M_ADDR_WIDTH({RAM_WIDTH}),
    .M_CONNECT_READ(1'b1),
    .M_CONNECT_WRITE(1'b1),
    .M_SECURE(1'b0)
)
axi_interconnect_inst (
    .clk(clk),
    .rst(~rstn),

    .s_axi_awid(reg_axi_awid),
    .s_axi_awaddr(reg_axi_awaddr),
    .s_axi_awlen(reg_axi_awlen),
    .s_axi_awsize(reg_axi_awsize),
    .s_axi_awburst(reg_axi_awburst),
    .s_axi_awlock(reg_axi_awlock),
    .s_axi_awcache(reg_axi_awcache),
    .s_axi_awprot(reg_axi_awprot),
    .s_axi_awqos(reg_axi_awqos),
    .s_axi_awuser(reg_axi_awuser),
    .s_axi_awvalid(reg_axi_awvalid),
    .s_axi_awready(reg_axi_awready),
    .s_axi_wdata(reg_axi_wdata),
    .s_axi_wstrb(reg_axi_wstrb),
    .s_axi_wlast(reg_axi_wlast),
    .s_axi_wuser(reg_axi_wuser),
    .s_axi_wvalid(reg_axi_wvalid),
    .s_axi_wready(reg_axi_wready),
    .s_axi_bid(reg_axi_bid),
    .s_axi_bresp(reg_axi_bresp),
    .s_axi_buser(reg_axi_buser),
    .s_axi_bvalid(reg_axi_bvalid),
    .s_axi_bready(reg_axi_bready),
    .s_axi_arid(reg_axi_arid),
    .s_axi_araddr(reg_axi_araddr),
    .s_axi_arlen(reg_axi_arlen),
    .s_axi_arsize(reg_axi_arsize),
    .s_axi_arburst(reg_axi_arburst),
    .s_axi_arlock(reg_axi_arlock),
    .s_axi_arcache(reg_axi_arcache),
    .s_axi_arprot(reg_axi_arprot),
    .s_axi_arqos(reg_axi_arqos),
    .s_axi_aruser(reg_axi_aruser),
    .s_axi_arvalid(reg_axi_arvalid),
    .s_axi_arready(reg_axi_arready),
    .s_axi_rid(reg_axi_rid),
    .s_axi_rdata(reg_axi_rdata),
    .s_axi_rresp(reg_axi_rresp),
    .s_axi_rlast(reg_axi_rlast),
    .s_axi_ruser(reg_axi_ruser),
    .s_axi_rvalid(reg_axi_rvalid),
    .s_axi_rready(reg_axi_rready),

    .m_axi_awid(int_axi_awid),
    .m_axi_awaddr(int_axi_awaddr),
    .m_axi_awlen(int_axi_awlen),
    .m_axi_awsize(int_axi_awsize),
    .m_axi_awburst(int_axi_awburst),
    .m_axi_awlock(int_axi_awlock),
    .m_axi_awcache(int_axi_awcache),
    .m_axi_awprot(int_axi_awprot),
    .m_axi_awregion(int_axi_awregion),
    .m_axi_awvalid(int_axi_awvalid),
    .m_axi_awready(int_axi_awready),
    .m_axi_wdata(int_axi_wdata),
    .m_axi_wstrb(int_axi_wstrb),
    .m_axi_wlast(int_axi_wlast),
    .m_axi_wvalid(int_axi_wvalid),
    .m_axi_wready(int_axi_wready),
    .m_axi_bid(int_axi_bid),
    .m_axi_bresp(int_axi_bresp),
    .m_axi_bvalid(int_axi_bvalid),
    .m_axi_bready(int_axi_bready),
    .m_axi_arid(int_axi_arid),
    .m_axi_araddr(int_axi_araddr),
    .m_axi_arlen(int_axi_arlen),
    .m_axi_arsize(int_axi_arsize),
    .m_axi_arburst(int_axi_arburst),
    .m_axi_arlock(int_axi_arlock),
    .m_axi_arcache(int_axi_arcache),
    .m_axi_arprot(int_axi_arprot),
    .m_axi_arregion(int_axi_arregion),
    .m_axi_arvalid(int_axi_arvalid),
    .m_axi_arready(int_axi_arready),
    .m_axi_rid(int_axi_rid),
    .m_axi_rdata(int_axi_rdata),
    .m_axi_rresp(int_axi_rresp),
    .m_axi_rlast(int_axi_rlast),
    .m_axi_rvalid(int_axi_rvalid),
    .m_axi_rready(int_axi_rready)
);

axi_ram #(
    .DATA_WIDTH(DATA_WIDTH),
    .ADDR_WIDTH(RAM_WIDTH),
    .STRB_WIDTH(STRB_WIDTH),
    .ID_WIDTH(ID_WIDTH),
    .PIPELINE_OUTPUT(RAM_PIPELINE_OUTPUT)
)
axi_ram_inst (
    .clk(clk),
    .rst(~rstn),

    .s_axi_awid(int_axi_awid),
    .s_axi_awaddr(int_axi_awaddr[RAM_WIDTH-1:0]),
    .s_axi_awlen(int_axi_awlen),
    .s_axi_awsize(int_axi_awsize),
    .s_axi_awburst(int_axi_awburst),
    .s_axi_awlock(int_axi_awlock),
    .s_axi_awcache(int_axi_awcache),
    .s_axi_awprot(int_axi_awprot),
    .s_axi_awvalid(int_axi_awvalid),
    .s_axi_awready(int_axi_awready),
    .s_axi_wdata(int_axi_wdata),
    .s_axi_wstrb(int_axi_wstrb),
    .s_axi_wlast(int_axi_wlast),
    .s_axi_wvalid(int_axi_wvalid),
    .s_axi_wready(int_axi_wready),
    .s_axi_bid(int_axi_bid),
    .s_axi_bresp(int_axi_bresp),
    .s_axi_bvalid(int_axi_bvalid),
    .s_axi_bready(int_axi_bready),
    .s_axi_arid(int_axi_arid),
    .s_axi_araddr(int_axi_araddr[RAM_WIDTH-1:0]),
    .s_axi_arlen(int_axi_arlen),
    .s_axi_arsize(int_axi_arsize),
    .s_axi_arburst(int_axi_arburst),
    .s_axi_arlock(int_axi_arlock),
    .s_axi_arcache(int_axi_arcache),
    .s_axi_arprot(int_axi_arprot),
    .s_axi_arvalid(int_axi_arvalid),
    .s_axi_arready(int_axi_arready),
    .s_axi_rid(int_axi_rid),
    .s_axi_rdata(int_axi_rdata),
    .s_axi_rresp(int_axi_rresp),
    .s_axi_rlast(int_axi_rlast),
    .s_axi_rvalid(int_axi_rvalid),
    .s_axi_rready(int_axi_rready)
);

`ifdef COCOTB_SIM
initial begin
    $dumpfile ("waveforms.vcd");
    $dumpvars;
end
`endif

endmodule
