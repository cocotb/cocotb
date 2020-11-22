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
 * AXI4 register (write)
 */
module axi_register_wr #
(
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
    // AW channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter AW_REG_TYPE = 1,
    // W channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter W_REG_TYPE = 2,
    // B channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter B_REG_TYPE = 1
)
(
    input  wire                     clk,
    input  wire                     rst,

    /*
     * AXI slave interface
     */
    input  wire [ID_WIDTH-1:0]      s_axi_awid,
    input  wire [ADDR_WIDTH-1:0]    s_axi_awaddr,
    input  wire [7:0]               s_axi_awlen,
    input  wire [2:0]               s_axi_awsize,
    input  wire [1:0]               s_axi_awburst,
    input  wire                     s_axi_awlock,
    input  wire [3:0]               s_axi_awcache,
    input  wire [2:0]               s_axi_awprot,
    input  wire [3:0]               s_axi_awqos,
    input  wire [3:0]               s_axi_awregion,
    input  wire [AWUSER_WIDTH-1:0]  s_axi_awuser,
    input  wire                     s_axi_awvalid,
    output wire                     s_axi_awready,
    input  wire [DATA_WIDTH-1:0]    s_axi_wdata,
    input  wire [STRB_WIDTH-1:0]    s_axi_wstrb,
    input  wire                     s_axi_wlast,
    input  wire [WUSER_WIDTH-1:0]   s_axi_wuser,
    input  wire                     s_axi_wvalid,
    output wire                     s_axi_wready,
    output wire [ID_WIDTH-1:0]      s_axi_bid,
    output wire [1:0]               s_axi_bresp,
    output wire [BUSER_WIDTH-1:0]   s_axi_buser,
    output wire                     s_axi_bvalid,
    input  wire                     s_axi_bready,

    /*
     * AXI master interface
     */
    output wire [ID_WIDTH-1:0]      m_axi_awid,
    output wire [ADDR_WIDTH-1:0]    m_axi_awaddr,
    output wire [7:0]               m_axi_awlen,
    output wire [2:0]               m_axi_awsize,
    output wire [1:0]               m_axi_awburst,
    output wire                     m_axi_awlock,
    output wire [3:0]               m_axi_awcache,
    output wire [2:0]               m_axi_awprot,
    output wire [3:0]               m_axi_awqos,
    output wire [3:0]               m_axi_awregion,
    output wire [AWUSER_WIDTH-1:0]  m_axi_awuser,
    output wire                     m_axi_awvalid,
    input  wire                     m_axi_awready,
    output wire [DATA_WIDTH-1:0]    m_axi_wdata,
    output wire [STRB_WIDTH-1:0]    m_axi_wstrb,
    output wire                     m_axi_wlast,
    output wire [WUSER_WIDTH-1:0]   m_axi_wuser,
    output wire                     m_axi_wvalid,
    input  wire                     m_axi_wready,
    input  wire [ID_WIDTH-1:0]      m_axi_bid,
    input  wire [1:0]               m_axi_bresp,
    input  wire [BUSER_WIDTH-1:0]   m_axi_buser,
    input  wire                     m_axi_bvalid,
    output wire                     m_axi_bready
);

generate

// AW channel

if (AW_REG_TYPE > 1) begin
// skid buffer, no bubble cycles

// datapath registers
reg                    s_axi_awready_reg = 1'b0;

reg [ID_WIDTH-1:0]     m_axi_awid_reg     = {ID_WIDTH{1'b0}};
reg [ADDR_WIDTH-1:0]   m_axi_awaddr_reg   = {ADDR_WIDTH{1'b0}};
reg [7:0]              m_axi_awlen_reg    = 8'd0;
reg [2:0]              m_axi_awsize_reg   = 3'd0;
reg [1:0]              m_axi_awburst_reg  = 2'd0;
reg                    m_axi_awlock_reg   = 1'b0;
reg [3:0]              m_axi_awcache_reg  = 4'd0;
reg [2:0]              m_axi_awprot_reg   = 3'd0;
reg [3:0]              m_axi_awqos_reg    = 4'd0;
reg [3:0]              m_axi_awregion_reg = 4'd0;
reg [AWUSER_WIDTH-1:0] m_axi_awuser_reg   = {AWUSER_WIDTH{1'b0}};
reg                    m_axi_awvalid_reg  = 1'b0, m_axi_awvalid_next;

reg [ID_WIDTH-1:0]     temp_m_axi_awid_reg     = {ID_WIDTH{1'b0}};
reg [ADDR_WIDTH-1:0]   temp_m_axi_awaddr_reg   = {ADDR_WIDTH{1'b0}};
reg [7:0]              temp_m_axi_awlen_reg    = 8'd0;
reg [2:0]              temp_m_axi_awsize_reg   = 3'd0;
reg [1:0]              temp_m_axi_awburst_reg  = 2'd0;
reg                    temp_m_axi_awlock_reg   = 1'b0;
reg [3:0]              temp_m_axi_awcache_reg  = 4'd0;
reg [2:0]              temp_m_axi_awprot_reg   = 3'd0;
reg [3:0]              temp_m_axi_awqos_reg    = 4'd0;
reg [3:0]              temp_m_axi_awregion_reg = 4'd0;
reg [AWUSER_WIDTH-1:0] temp_m_axi_awuser_reg   = {AWUSER_WIDTH{1'b0}};
reg                    temp_m_axi_awvalid_reg  = 1'b0, temp_m_axi_awvalid_next;

// datapath control
reg store_axi_aw_input_to_output;
reg store_axi_aw_input_to_temp;
reg store_axi_aw_temp_to_output;

assign s_axi_awready  = s_axi_awready_reg;

assign m_axi_awid     = m_axi_awid_reg;
assign m_axi_awaddr   = m_axi_awaddr_reg;
assign m_axi_awlen    = m_axi_awlen_reg;
assign m_axi_awsize   = m_axi_awsize_reg;
assign m_axi_awburst  = m_axi_awburst_reg;
assign m_axi_awlock   = m_axi_awlock_reg;
assign m_axi_awcache  = m_axi_awcache_reg;
assign m_axi_awprot   = m_axi_awprot_reg;
assign m_axi_awqos    = m_axi_awqos_reg;
assign m_axi_awregion = m_axi_awregion_reg;
assign m_axi_awuser   = AWUSER_ENABLE ? m_axi_awuser_reg : {AWUSER_WIDTH{1'b0}};
assign m_axi_awvalid  = m_axi_awvalid_reg;

// enable ready input next cycle if output is ready or the temp reg will not be filled on the next cycle (output reg empty or no input)
wire s_axi_awready_early = m_axi_awready | (~temp_m_axi_awvalid_reg & (~m_axi_awvalid_reg | ~s_axi_awvalid));

always @* begin
    // transfer sink ready state to source
    m_axi_awvalid_next = m_axi_awvalid_reg;
    temp_m_axi_awvalid_next = temp_m_axi_awvalid_reg;

    store_axi_aw_input_to_output = 1'b0;
    store_axi_aw_input_to_temp = 1'b0;
    store_axi_aw_temp_to_output = 1'b0;

    if (s_axi_awready_reg) begin
        // input is ready
        if (m_axi_awready | ~m_axi_awvalid_reg) begin
            // output is ready or currently not valid, transfer data to output
            m_axi_awvalid_next = s_axi_awvalid;
            store_axi_aw_input_to_output = 1'b1;
        end else begin
            // output is not ready, store input in temp
            temp_m_axi_awvalid_next = s_axi_awvalid;
            store_axi_aw_input_to_temp = 1'b1;
        end
    end else if (m_axi_awready) begin
        // input is not ready, but output is ready
        m_axi_awvalid_next = temp_m_axi_awvalid_reg;
        temp_m_axi_awvalid_next = 1'b0;
        store_axi_aw_temp_to_output = 1'b1;
    end
end

always @(posedge clk) begin
    if (rst) begin
        s_axi_awready_reg <= 1'b0;
        m_axi_awvalid_reg <= 1'b0;
        temp_m_axi_awvalid_reg <= 1'b0;
    end else begin
        s_axi_awready_reg <= s_axi_awready_early;
        m_axi_awvalid_reg <= m_axi_awvalid_next;
        temp_m_axi_awvalid_reg <= temp_m_axi_awvalid_next;
    end

    // datapath
    if (store_axi_aw_input_to_output) begin
        m_axi_awid_reg <= s_axi_awid;
        m_axi_awaddr_reg <= s_axi_awaddr;
        m_axi_awlen_reg <= s_axi_awlen;
        m_axi_awsize_reg <= s_axi_awsize;
        m_axi_awburst_reg <= s_axi_awburst;
        m_axi_awlock_reg <= s_axi_awlock;
        m_axi_awcache_reg <= s_axi_awcache;
        m_axi_awprot_reg <= s_axi_awprot;
        m_axi_awqos_reg <= s_axi_awqos;
        m_axi_awregion_reg <= s_axi_awregion;
        m_axi_awuser_reg <= s_axi_awuser;
    end else if (store_axi_aw_temp_to_output) begin
        m_axi_awid_reg <= temp_m_axi_awid_reg;
        m_axi_awaddr_reg <= temp_m_axi_awaddr_reg;
        m_axi_awlen_reg <= temp_m_axi_awlen_reg;
        m_axi_awsize_reg <= temp_m_axi_awsize_reg;
        m_axi_awburst_reg <= temp_m_axi_awburst_reg;
        m_axi_awlock_reg <= temp_m_axi_awlock_reg;
        m_axi_awcache_reg <= temp_m_axi_awcache_reg;
        m_axi_awprot_reg <= temp_m_axi_awprot_reg;
        m_axi_awqos_reg <= temp_m_axi_awqos_reg;
        m_axi_awregion_reg <= temp_m_axi_awregion_reg;
        m_axi_awuser_reg <= temp_m_axi_awuser_reg;
    end

    if (store_axi_aw_input_to_temp) begin
        temp_m_axi_awid_reg <= s_axi_awid;
        temp_m_axi_awaddr_reg <= s_axi_awaddr;
        temp_m_axi_awlen_reg <= s_axi_awlen;
        temp_m_axi_awsize_reg <= s_axi_awsize;
        temp_m_axi_awburst_reg <= s_axi_awburst;
        temp_m_axi_awlock_reg <= s_axi_awlock;
        temp_m_axi_awcache_reg <= s_axi_awcache;
        temp_m_axi_awprot_reg <= s_axi_awprot;
        temp_m_axi_awqos_reg <= s_axi_awqos;
        temp_m_axi_awregion_reg <= s_axi_awregion;
        temp_m_axi_awuser_reg <= s_axi_awuser;
    end
end

end else if (AW_REG_TYPE == 1) begin
// simple register, inserts bubble cycles

// datapath registers
reg                    s_axi_awready_reg = 1'b0;

reg [ID_WIDTH-1:0]     m_axi_awid_reg     = {ID_WIDTH{1'b0}};
reg [ADDR_WIDTH-1:0]   m_axi_awaddr_reg   = {ADDR_WIDTH{1'b0}};
reg [7:0]              m_axi_awlen_reg    = 8'd0;
reg [2:0]              m_axi_awsize_reg   = 3'd0;
reg [1:0]              m_axi_awburst_reg  = 2'd0;
reg                    m_axi_awlock_reg   = 1'b0;
reg [3:0]              m_axi_awcache_reg  = 4'd0;
reg [2:0]              m_axi_awprot_reg   = 3'd0;
reg [3:0]              m_axi_awqos_reg    = 4'd0;
reg [3:0]              m_axi_awregion_reg = 4'd0;
reg [AWUSER_WIDTH-1:0] m_axi_awuser_reg   = {AWUSER_WIDTH{1'b0}};
reg                    m_axi_awvalid_reg  = 1'b0, m_axi_awvalid_next;

// datapath control
reg store_axi_aw_input_to_output;

assign s_axi_awready  = s_axi_awready_reg;

assign m_axi_awid     = m_axi_awid_reg;
assign m_axi_awaddr   = m_axi_awaddr_reg;
assign m_axi_awlen    = m_axi_awlen_reg;
assign m_axi_awsize   = m_axi_awsize_reg;
assign m_axi_awburst  = m_axi_awburst_reg;
assign m_axi_awlock   = m_axi_awlock_reg;
assign m_axi_awcache  = m_axi_awcache_reg;
assign m_axi_awprot   = m_axi_awprot_reg;
assign m_axi_awqos    = m_axi_awqos_reg;
assign m_axi_awregion = m_axi_awregion_reg;
assign m_axi_awuser   = AWUSER_ENABLE ? m_axi_awuser_reg : {AWUSER_WIDTH{1'b0}};
assign m_axi_awvalid  = m_axi_awvalid_reg;

// enable ready input next cycle if output buffer will be empty
wire s_axi_awready_eawly = !m_axi_awvalid_next;

always @* begin
    // transfer sink ready state to source
    m_axi_awvalid_next = m_axi_awvalid_reg;

    store_axi_aw_input_to_output = 1'b0;

    if (s_axi_awready_reg) begin
        m_axi_awvalid_next = s_axi_awvalid;
        store_axi_aw_input_to_output = 1'b1;
    end else if (m_axi_awready) begin
        m_axi_awvalid_next = 1'b0;
    end
end

always @(posedge clk) begin
    if (rst) begin
        s_axi_awready_reg <= 1'b0;
        m_axi_awvalid_reg <= 1'b0;
    end else begin
        s_axi_awready_reg <= s_axi_awready_eawly;
        m_axi_awvalid_reg <= m_axi_awvalid_next;
    end

    // datapath
    if (store_axi_aw_input_to_output) begin
        m_axi_awid_reg <= s_axi_awid;
        m_axi_awaddr_reg <= s_axi_awaddr;
        m_axi_awlen_reg <= s_axi_awlen;
        m_axi_awsize_reg <= s_axi_awsize;
        m_axi_awburst_reg <= s_axi_awburst;
        m_axi_awlock_reg <= s_axi_awlock;
        m_axi_awcache_reg <= s_axi_awcache;
        m_axi_awprot_reg <= s_axi_awprot;
        m_axi_awqos_reg <= s_axi_awqos;
        m_axi_awregion_reg <= s_axi_awregion;
        m_axi_awuser_reg <= s_axi_awuser;
    end
end

end else begin

    // bypass AW channel
    assign m_axi_awid = s_axi_awid;
    assign m_axi_awaddr = s_axi_awaddr;
    assign m_axi_awlen = s_axi_awlen;
    assign m_axi_awsize = s_axi_awsize;
    assign m_axi_awburst = s_axi_awburst;
    assign m_axi_awlock = s_axi_awlock;
    assign m_axi_awcache = s_axi_awcache;
    assign m_axi_awprot = s_axi_awprot;
    assign m_axi_awqos = s_axi_awqos;
    assign m_axi_awregion = s_axi_awregion;
    assign m_axi_awuser = AWUSER_ENABLE ? s_axi_awuser : {AWUSER_WIDTH{1'b0}};
    assign m_axi_awvalid = s_axi_awvalid;
    assign s_axi_awready = m_axi_awready;

end

// W channel

if (W_REG_TYPE > 1) begin
// skid buffer, no bubble cycles

// datapath registers
reg                   s_axi_wready_reg = 1'b0;

reg [DATA_WIDTH-1:0]  m_axi_wdata_reg  = {DATA_WIDTH{1'b0}};
reg [STRB_WIDTH-1:0]  m_axi_wstrb_reg  = {STRB_WIDTH{1'b0}};
reg                   m_axi_wlast_reg  = 1'b0;
reg [WUSER_WIDTH-1:0] m_axi_wuser_reg  = {WUSER_WIDTH{1'b0}};
reg                   m_axi_wvalid_reg = 1'b0, m_axi_wvalid_next;

reg [DATA_WIDTH-1:0]  temp_m_axi_wdata_reg  = {DATA_WIDTH{1'b0}};
reg [STRB_WIDTH-1:0]  temp_m_axi_wstrb_reg  = {STRB_WIDTH{1'b0}};
reg                   temp_m_axi_wlast_reg  = 1'b0;
reg [WUSER_WIDTH-1:0] temp_m_axi_wuser_reg  = {WUSER_WIDTH{1'b0}};
reg                   temp_m_axi_wvalid_reg = 1'b0, temp_m_axi_wvalid_next;

// datapath control
reg store_axi_w_input_to_output;
reg store_axi_w_input_to_temp;
reg store_axi_w_temp_to_output;

assign s_axi_wready = s_axi_wready_reg;

assign m_axi_wdata  = m_axi_wdata_reg;
assign m_axi_wstrb  = m_axi_wstrb_reg;
assign m_axi_wlast  = m_axi_wlast_reg;
assign m_axi_wuser  = WUSER_ENABLE ? m_axi_wuser_reg : {WUSER_WIDTH{1'b0}};
assign m_axi_wvalid = m_axi_wvalid_reg;

// enable ready input next cycle if output is ready or the temp reg will not be filled on the next cycle (output reg empty or no input)
wire s_axi_wready_early = m_axi_wready | (~temp_m_axi_wvalid_reg & (~m_axi_wvalid_reg | ~s_axi_wvalid));

always @* begin
    // transfer sink ready state to source
    m_axi_wvalid_next = m_axi_wvalid_reg;
    temp_m_axi_wvalid_next = temp_m_axi_wvalid_reg;

    store_axi_w_input_to_output = 1'b0;
    store_axi_w_input_to_temp = 1'b0;
    store_axi_w_temp_to_output = 1'b0;

    if (s_axi_wready_reg) begin
        // input is ready
        if (m_axi_wready | ~m_axi_wvalid_reg) begin
            // output is ready or currently not valid, transfer data to output
            m_axi_wvalid_next = s_axi_wvalid;
            store_axi_w_input_to_output = 1'b1;
        end else begin
            // output is not ready, store input in temp
            temp_m_axi_wvalid_next = s_axi_wvalid;
            store_axi_w_input_to_temp = 1'b1;
        end
    end else if (m_axi_wready) begin
        // input is not ready, but output is ready
        m_axi_wvalid_next = temp_m_axi_wvalid_reg;
        temp_m_axi_wvalid_next = 1'b0;
        store_axi_w_temp_to_output = 1'b1;
    end
end

always @(posedge clk) begin
    if (rst) begin
        s_axi_wready_reg <= 1'b0;
        m_axi_wvalid_reg <= 1'b0;
        temp_m_axi_wvalid_reg <= 1'b0;
    end else begin
        s_axi_wready_reg <= s_axi_wready_early;
        m_axi_wvalid_reg <= m_axi_wvalid_next;
        temp_m_axi_wvalid_reg <= temp_m_axi_wvalid_next;
    end

    // datapath
    if (store_axi_w_input_to_output) begin
        m_axi_wdata_reg <= s_axi_wdata;
        m_axi_wstrb_reg <= s_axi_wstrb;
        m_axi_wlast_reg <= s_axi_wlast;
        m_axi_wuser_reg <= s_axi_wuser;
    end else if (store_axi_w_temp_to_output) begin
        m_axi_wdata_reg <= temp_m_axi_wdata_reg;
        m_axi_wstrb_reg <= temp_m_axi_wstrb_reg;
        m_axi_wlast_reg <= temp_m_axi_wlast_reg;
        m_axi_wuser_reg <= temp_m_axi_wuser_reg;
    end

    if (store_axi_w_input_to_temp) begin
        temp_m_axi_wdata_reg <= s_axi_wdata;
        temp_m_axi_wstrb_reg <= s_axi_wstrb;
        temp_m_axi_wlast_reg <= s_axi_wlast;
        temp_m_axi_wuser_reg <= s_axi_wuser;
    end
end

end else if (W_REG_TYPE == 1) begin
// simple register, inserts bubble cycles

// datapath registers
reg                   s_axi_wready_reg = 1'b0;

reg [DATA_WIDTH-1:0]  m_axi_wdata_reg  = {DATA_WIDTH{1'b0}};
reg [STRB_WIDTH-1:0]  m_axi_wstrb_reg  = {STRB_WIDTH{1'b0}};
reg                   m_axi_wlast_reg  = 1'b0;
reg [WUSER_WIDTH-1:0] m_axi_wuser_reg  = {WUSER_WIDTH{1'b0}};
reg                   m_axi_wvalid_reg = 1'b0, m_axi_wvalid_next;

// datapath control
reg store_axi_w_input_to_output;

assign s_axi_wready = s_axi_wready_reg;

assign m_axi_wdata  = m_axi_wdata_reg;
assign m_axi_wstrb  = m_axi_wstrb_reg;
assign m_axi_wlast  = m_axi_wlast_reg;
assign m_axi_wuser  = WUSER_ENABLE ? m_axi_wuser_reg : {WUSER_WIDTH{1'b0}};
assign m_axi_wvalid = m_axi_wvalid_reg;

// enable ready input next cycle if output buffer will be empty
wire s_axi_wready_ewly = !m_axi_wvalid_next;

always @* begin
    // transfer sink ready state to source
    m_axi_wvalid_next = m_axi_wvalid_reg;

    store_axi_w_input_to_output = 1'b0;

    if (s_axi_wready_reg) begin
        m_axi_wvalid_next = s_axi_wvalid;
        store_axi_w_input_to_output = 1'b1;
    end else if (m_axi_wready) begin
        m_axi_wvalid_next = 1'b0;
    end
end

always @(posedge clk) begin
    if (rst) begin
        s_axi_wready_reg <= 1'b0;
        m_axi_wvalid_reg <= 1'b0;
    end else begin
        s_axi_wready_reg <= s_axi_wready_ewly;
        m_axi_wvalid_reg <= m_axi_wvalid_next;
    end

    // datapath
    if (store_axi_w_input_to_output) begin
        m_axi_wdata_reg <= s_axi_wdata;
        m_axi_wstrb_reg <= s_axi_wstrb;
        m_axi_wlast_reg <= s_axi_wlast;
        m_axi_wuser_reg <= s_axi_wuser;
    end
end

end else begin

    // bypass W channel
    assign m_axi_wdata = s_axi_wdata;
    assign m_axi_wstrb = s_axi_wstrb;
    assign m_axi_wlast = s_axi_wlast;
    assign m_axi_wuser = WUSER_ENABLE ? s_axi_wuser : {WUSER_WIDTH{1'b0}};
    assign m_axi_wvalid = s_axi_wvalid;
    assign s_axi_wready = m_axi_wready;

end

// B channel

if (B_REG_TYPE > 1) begin
// skid buffer, no bubble cycles

// datapath registers
reg                   m_axi_bready_reg = 1'b0;

reg [ID_WIDTH-1:0]    s_axi_bid_reg    = {ID_WIDTH{1'b0}};
reg [1:0]             s_axi_bresp_reg  = 2'b0;
reg [BUSER_WIDTH-1:0] s_axi_buser_reg  = {BUSER_WIDTH{1'b0}};
reg                   s_axi_bvalid_reg = 1'b0, s_axi_bvalid_next;

reg [ID_WIDTH-1:0]    temp_s_axi_bid_reg    = {ID_WIDTH{1'b0}};
reg [1:0]             temp_s_axi_bresp_reg  = 2'b0;
reg [BUSER_WIDTH-1:0] temp_s_axi_buser_reg  = {BUSER_WIDTH{1'b0}};
reg                   temp_s_axi_bvalid_reg = 1'b0, temp_s_axi_bvalid_next;

// datapath control
reg store_axi_b_input_to_output;
reg store_axi_b_input_to_temp;
reg store_axi_b_temp_to_output;

assign m_axi_bready = m_axi_bready_reg;

assign s_axi_bid    = s_axi_bid_reg;
assign s_axi_bresp  = s_axi_bresp_reg;
assign s_axi_buser  = BUSER_ENABLE ? s_axi_buser_reg : {BUSER_WIDTH{1'b0}};
assign s_axi_bvalid = s_axi_bvalid_reg;

// enable ready input next cycle if output is ready or the temp reg will not be filled on the next cycle (output reg empty or no input)
wire m_axi_bready_early = s_axi_bready | (~temp_s_axi_bvalid_reg & (~s_axi_bvalid_reg | ~m_axi_bvalid));

always @* begin
    // transfer sink ready state to source
    s_axi_bvalid_next = s_axi_bvalid_reg;
    temp_s_axi_bvalid_next = temp_s_axi_bvalid_reg;

    store_axi_b_input_to_output = 1'b0;
    store_axi_b_input_to_temp = 1'b0;
    store_axi_b_temp_to_output = 1'b0;

    if (m_axi_bready_reg) begin
        // input is ready
        if (s_axi_bready | ~s_axi_bvalid_reg) begin
            // output is ready or currently not valid, transfer data to output
            s_axi_bvalid_next = m_axi_bvalid;
            store_axi_b_input_to_output = 1'b1;
        end else begin
            // output is not ready, store input in temp
            temp_s_axi_bvalid_next = m_axi_bvalid;
            store_axi_b_input_to_temp = 1'b1;
        end
    end else if (s_axi_bready) begin
        // input is not ready, but output is ready
        s_axi_bvalid_next = temp_s_axi_bvalid_reg;
        temp_s_axi_bvalid_next = 1'b0;
        store_axi_b_temp_to_output = 1'b1;
    end
end

always @(posedge clk) begin
    if (rst) begin
        m_axi_bready_reg <= 1'b0;
        s_axi_bvalid_reg <= 1'b0;
        temp_s_axi_bvalid_reg <= 1'b0;
    end else begin
        m_axi_bready_reg <= m_axi_bready_early;
        s_axi_bvalid_reg <= s_axi_bvalid_next;
        temp_s_axi_bvalid_reg <= temp_s_axi_bvalid_next;
    end

    // datapath
    if (store_axi_b_input_to_output) begin
        s_axi_bid_reg   <= m_axi_bid;
        s_axi_bresp_reg <= m_axi_bresp;
        s_axi_buser_reg <= m_axi_buser;
    end else if (store_axi_b_temp_to_output) begin
        s_axi_bid_reg   <= temp_s_axi_bid_reg;
        s_axi_bresp_reg <= temp_s_axi_bresp_reg;
        s_axi_buser_reg <= temp_s_axi_buser_reg;
    end

    if (store_axi_b_input_to_temp) begin
        temp_s_axi_bid_reg   <= m_axi_bid;
        temp_s_axi_bresp_reg <= m_axi_bresp;
        temp_s_axi_buser_reg <= m_axi_buser;
    end
end

end else if (B_REG_TYPE == 1) begin
// simple register, inserts bubble cycles

// datapath registers
reg                   m_axi_bready_reg = 1'b0;

reg [ID_WIDTH-1:0]    s_axi_bid_reg    = {ID_WIDTH{1'b0}};
reg [1:0]             s_axi_bresp_reg  = 2'b0;
reg [BUSER_WIDTH-1:0] s_axi_buser_reg  = {BUSER_WIDTH{1'b0}};
reg                   s_axi_bvalid_reg = 1'b0, s_axi_bvalid_next;

// datapath control
reg store_axi_b_input_to_output;

assign m_axi_bready = m_axi_bready_reg;

assign s_axi_bid    = s_axi_bid_reg;
assign s_axi_bresp  = s_axi_bresp_reg;
assign s_axi_buser  = BUSER_ENABLE ? s_axi_buser_reg : {BUSER_WIDTH{1'b0}};
assign s_axi_bvalid = s_axi_bvalid_reg;

// enable ready input next cycle if output buffer will be empty
wire m_axi_bready_early = !s_axi_bvalid_next;

always @* begin
    // transfer sink ready state to source
    s_axi_bvalid_next = s_axi_bvalid_reg;

    store_axi_b_input_to_output = 1'b0;

    if (m_axi_bready_reg) begin
        s_axi_bvalid_next = m_axi_bvalid;
        store_axi_b_input_to_output = 1'b1;
    end else if (s_axi_bready) begin
        s_axi_bvalid_next = 1'b0;
    end
end

always @(posedge clk) begin
    if (rst) begin
        m_axi_bready_reg <= 1'b0;
        s_axi_bvalid_reg <= 1'b0;
    end else begin
        m_axi_bready_reg <= m_axi_bready_early;
        s_axi_bvalid_reg <= s_axi_bvalid_next;
    end

    // datapath
    if (store_axi_b_input_to_output) begin
        s_axi_bid_reg   <= m_axi_bid;
        s_axi_bresp_reg <= m_axi_bresp;
        s_axi_buser_reg <= m_axi_buser;
    end
end

end else begin

    // bypass B channel
    assign s_axi_bid = m_axi_bid;
    assign s_axi_bresp = m_axi_bresp;
    assign s_axi_buser = BUSER_ENABLE ? m_axi_buser : {BUSER_WIDTH{1'b0}};
    assign s_axi_bvalid = m_axi_bvalid;
    assign m_axi_bready = s_axi_bready;

end

endgenerate

endmodule
