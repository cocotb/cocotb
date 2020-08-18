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
 * AXI4 register (read)
 */
module axi_register_rd #
(
    // Width of data bus in bits
    parameter DATA_WIDTH = 32,
    // Width of address bus in bits
    parameter ADDR_WIDTH = 32,
    // Width of wstrb (width of data bus in words)
    parameter STRB_WIDTH = (DATA_WIDTH/8),
    // Width of ID signal
    parameter ID_WIDTH = 8,
    // Propagate aruser signal
    parameter ARUSER_ENABLE = 0,
    // Width of aruser signal
    parameter ARUSER_WIDTH = 1,
    // Propagate ruser signal
    parameter RUSER_ENABLE = 0,
    // Width of ruser signal
    parameter RUSER_WIDTH = 1,
    // AR channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter AR_REG_TYPE = 1,
    // R channel register type
    // 0 to bypass, 1 for simple buffer, 2 for skid buffer
    parameter R_REG_TYPE = 2
)
(
    input  wire                     clk,
    input  wire                     rst,

    /*
     * AXI slave interface
     */
    input  wire [ID_WIDTH-1:0]      s_axi_arid,
    input  wire [ADDR_WIDTH-1:0]    s_axi_araddr,
    input  wire [7:0]               s_axi_arlen,
    input  wire [2:0]               s_axi_arsize,
    input  wire [1:0]               s_axi_arburst,
    input  wire                     s_axi_arlock,
    input  wire [3:0]               s_axi_arcache,
    input  wire [2:0]               s_axi_arprot,
    input  wire [3:0]               s_axi_arqos,
    input  wire [3:0]               s_axi_arregion,
    input  wire [ARUSER_WIDTH-1:0]  s_axi_aruser,
    input  wire                     s_axi_arvalid,
    output wire                     s_axi_arready,
    output wire [ID_WIDTH-1:0]      s_axi_rid,
    output wire [DATA_WIDTH-1:0]    s_axi_rdata,
    output wire [1:0]               s_axi_rresp,
    output wire                     s_axi_rlast,
    output wire [RUSER_WIDTH-1:0]   s_axi_ruser,
    output wire                     s_axi_rvalid,
    input  wire                     s_axi_rready,

    /*
     * AXI master interface
     */
    output wire [ID_WIDTH-1:0]      m_axi_arid,
    output wire [ADDR_WIDTH-1:0]    m_axi_araddr,
    output wire [7:0]               m_axi_arlen,
    output wire [2:0]               m_axi_arsize,
    output wire [1:0]               m_axi_arburst,
    output wire                     m_axi_arlock,
    output wire [3:0]               m_axi_arcache,
    output wire [2:0]               m_axi_arprot,
    output wire [3:0]               m_axi_arqos,
    output wire [3:0]               m_axi_arregion,
    output wire [ARUSER_WIDTH-1:0]  m_axi_aruser,
    output wire                     m_axi_arvalid,
    input  wire                     m_axi_arready,
    input  wire [ID_WIDTH-1:0]      m_axi_rid,
    input  wire [DATA_WIDTH-1:0]    m_axi_rdata,
    input  wire [1:0]               m_axi_rresp,
    input  wire                     m_axi_rlast,
    input  wire [RUSER_WIDTH-1:0]   m_axi_ruser,
    input  wire                     m_axi_rvalid,
    output wire                     m_axi_rready
);

generate

// AR channel

if (AR_REG_TYPE > 1) begin
// skid buffer, no bubble cycles

// datapath registers
reg                    s_axi_arready_reg = 1'b0;

reg [ID_WIDTH-1:0]     m_axi_arid_reg     = {ID_WIDTH{1'b0}};
reg [ADDR_WIDTH-1:0]   m_axi_araddr_reg   = {ADDR_WIDTH{1'b0}};
reg [7:0]              m_axi_arlen_reg    = 8'd0;
reg [2:0]              m_axi_arsize_reg   = 3'd0;
reg [1:0]              m_axi_arburst_reg  = 2'd0;
reg                    m_axi_arlock_reg   = 1'b0;
reg [3:0]              m_axi_arcache_reg  = 4'd0;
reg [2:0]              m_axi_arprot_reg   = 3'd0;
reg [3:0]              m_axi_arqos_reg    = 4'd0;
reg [3:0]              m_axi_arregion_reg = 4'd0;
reg [ARUSER_WIDTH-1:0] m_axi_aruser_reg   = {ARUSER_WIDTH{1'b0}};
reg                    m_axi_arvalid_reg  = 1'b0, m_axi_arvalid_next;

reg [ID_WIDTH-1:0]     temp_m_axi_arid_reg     = {ID_WIDTH{1'b0}};
reg [ADDR_WIDTH-1:0]   temp_m_axi_araddr_reg   = {ADDR_WIDTH{1'b0}};
reg [7:0]              temp_m_axi_arlen_reg    = 8'd0;
reg [2:0]              temp_m_axi_arsize_reg   = 3'd0;
reg [1:0]              temp_m_axi_arburst_reg  = 2'd0;
reg                    temp_m_axi_arlock_reg   = 1'b0;
reg [3:0]              temp_m_axi_arcache_reg  = 4'd0;
reg [2:0]              temp_m_axi_arprot_reg   = 3'd0;
reg [3:0]              temp_m_axi_arqos_reg    = 4'd0;
reg [3:0]              temp_m_axi_arregion_reg = 4'd0;
reg [ARUSER_WIDTH-1:0] temp_m_axi_aruser_reg   = {ARUSER_WIDTH{1'b0}};
reg                    temp_m_axi_arvalid_reg  = 1'b0, temp_m_axi_arvalid_next;

// datapath control
reg store_axi_ar_input_to_output;
reg store_axi_ar_input_to_temp;
reg store_axi_ar_temp_to_output;

assign s_axi_arready  = s_axi_arready_reg;

assign m_axi_arid     = m_axi_arid_reg;
assign m_axi_araddr   = m_axi_araddr_reg;
assign m_axi_arlen    = m_axi_arlen_reg;
assign m_axi_arsize   = m_axi_arsize_reg;
assign m_axi_arburst  = m_axi_arburst_reg;
assign m_axi_arlock   = m_axi_arlock_reg;
assign m_axi_arcache  = m_axi_arcache_reg;
assign m_axi_arprot   = m_axi_arprot_reg;
assign m_axi_arqos    = m_axi_arqos_reg;
assign m_axi_arregion = m_axi_arregion_reg;
assign m_axi_aruser   = ARUSER_ENABLE ? m_axi_aruser_reg : {ARUSER_WIDTH{1'b0}};
assign m_axi_arvalid  = m_axi_arvalid_reg;

// enable ready input next cycle if output is ready or the temp reg will not be filled on the next cycle (output reg empty or no input)
wire s_axi_arready_early = m_axi_arready | (~temp_m_axi_arvalid_reg & (~m_axi_arvalid_reg | ~s_axi_arvalid));

always @* begin
    // transfer sink ready state to source
    m_axi_arvalid_next = m_axi_arvalid_reg;
    temp_m_axi_arvalid_next = temp_m_axi_arvalid_reg;

    store_axi_ar_input_to_output = 1'b0;
    store_axi_ar_input_to_temp = 1'b0;
    store_axi_ar_temp_to_output = 1'b0;

    if (s_axi_arready_reg) begin
        // input is ready
        if (m_axi_arready | ~m_axi_arvalid_reg) begin
            // output is ready or currently not valid, transfer data to output
            m_axi_arvalid_next = s_axi_arvalid;
            store_axi_ar_input_to_output = 1'b1;
        end else begin
            // output is not ready, store input in temp
            temp_m_axi_arvalid_next = s_axi_arvalid;
            store_axi_ar_input_to_temp = 1'b1;
        end
    end else if (m_axi_arready) begin
        // input is not ready, but output is ready
        m_axi_arvalid_next = temp_m_axi_arvalid_reg;
        temp_m_axi_arvalid_next = 1'b0;
        store_axi_ar_temp_to_output = 1'b1;
    end
end

always @(posedge clk) begin
    if (rst) begin
        s_axi_arready_reg <= 1'b0;
        m_axi_arvalid_reg <= 1'b0;
        temp_m_axi_arvalid_reg <= 1'b0;
    end else begin
        s_axi_arready_reg <= s_axi_arready_early;
        m_axi_arvalid_reg <= m_axi_arvalid_next;
        temp_m_axi_arvalid_reg <= temp_m_axi_arvalid_next;
    end

    // datapath
    if (store_axi_ar_input_to_output) begin
        m_axi_arid_reg <= s_axi_arid;
        m_axi_araddr_reg <= s_axi_araddr;
        m_axi_arlen_reg <= s_axi_arlen;
        m_axi_arsize_reg <= s_axi_arsize;
        m_axi_arburst_reg <= s_axi_arburst;
        m_axi_arlock_reg <= s_axi_arlock;
        m_axi_arcache_reg <= s_axi_arcache;
        m_axi_arprot_reg <= s_axi_arprot;
        m_axi_arqos_reg <= s_axi_arqos;
        m_axi_arregion_reg <= s_axi_arregion;
        m_axi_aruser_reg <= s_axi_aruser;
    end else if (store_axi_ar_temp_to_output) begin
        m_axi_arid_reg <= temp_m_axi_arid_reg;
        m_axi_araddr_reg <= temp_m_axi_araddr_reg;
        m_axi_arlen_reg <= temp_m_axi_arlen_reg;
        m_axi_arsize_reg <= temp_m_axi_arsize_reg;
        m_axi_arburst_reg <= temp_m_axi_arburst_reg;
        m_axi_arlock_reg <= temp_m_axi_arlock_reg;
        m_axi_arcache_reg <= temp_m_axi_arcache_reg;
        m_axi_arprot_reg <= temp_m_axi_arprot_reg;
        m_axi_arqos_reg <= temp_m_axi_arqos_reg;
        m_axi_arregion_reg <= temp_m_axi_arregion_reg;
        m_axi_aruser_reg <= temp_m_axi_aruser_reg;
    end

    if (store_axi_ar_input_to_temp) begin
        temp_m_axi_arid_reg <= s_axi_arid;
        temp_m_axi_araddr_reg <= s_axi_araddr;
        temp_m_axi_arlen_reg <= s_axi_arlen;
        temp_m_axi_arsize_reg <= s_axi_arsize;
        temp_m_axi_arburst_reg <= s_axi_arburst;
        temp_m_axi_arlock_reg <= s_axi_arlock;
        temp_m_axi_arcache_reg <= s_axi_arcache;
        temp_m_axi_arprot_reg <= s_axi_arprot;
        temp_m_axi_arqos_reg <= s_axi_arqos;
        temp_m_axi_arregion_reg <= s_axi_arregion;
        temp_m_axi_aruser_reg <= s_axi_aruser;
    end
end

end else if (AR_REG_TYPE == 1) begin
// simple register, inserts bubble cycles

// datapath registers
reg                    s_axi_arready_reg = 1'b0;

reg [ID_WIDTH-1:0]     m_axi_arid_reg     = {ID_WIDTH{1'b0}};
reg [ADDR_WIDTH-1:0]   m_axi_araddr_reg   = {ADDR_WIDTH{1'b0}};
reg [7:0]              m_axi_arlen_reg    = 8'd0;
reg [2:0]              m_axi_arsize_reg   = 3'd0;
reg [1:0]              m_axi_arburst_reg  = 2'd0;
reg                    m_axi_arlock_reg   = 1'b0;
reg [3:0]              m_axi_arcache_reg  = 4'd0;
reg [2:0]              m_axi_arprot_reg   = 3'd0;
reg [3:0]              m_axi_arqos_reg    = 4'd0;
reg [3:0]              m_axi_arregion_reg = 4'd0;
reg [ARUSER_WIDTH-1:0] m_axi_aruser_reg   = {ARUSER_WIDTH{1'b0}};
reg                    m_axi_arvalid_reg  = 1'b0, m_axi_arvalid_next;

// datapath control
reg store_axi_ar_input_to_output;

assign s_axi_arready  = s_axi_arready_reg;

assign m_axi_arid     = m_axi_arid_reg;
assign m_axi_araddr   = m_axi_araddr_reg;
assign m_axi_arlen    = m_axi_arlen_reg;
assign m_axi_arsize   = m_axi_arsize_reg;
assign m_axi_arburst  = m_axi_arburst_reg;
assign m_axi_arlock   = m_axi_arlock_reg;
assign m_axi_arcache  = m_axi_arcache_reg;
assign m_axi_arprot   = m_axi_arprot_reg;
assign m_axi_arqos    = m_axi_arqos_reg;
assign m_axi_arregion = m_axi_arregion_reg;
assign m_axi_aruser   = ARUSER_ENABLE ? m_axi_aruser_reg : {ARUSER_WIDTH{1'b0}};
assign m_axi_arvalid  = m_axi_arvalid_reg;

// enable ready input next cycle if output buffer will be empty
wire s_axi_arready_early = !m_axi_arvalid_next;

always @* begin
    // transfer sink ready state to source
    m_axi_arvalid_next = m_axi_arvalid_reg;

    store_axi_ar_input_to_output = 1'b0;

    if (s_axi_arready_reg) begin
        m_axi_arvalid_next = s_axi_arvalid;
        store_axi_ar_input_to_output = 1'b1;
    end else if (m_axi_arready) begin
        m_axi_arvalid_next = 1'b0;
    end
end

always @(posedge clk) begin
    if (rst) begin
        s_axi_arready_reg <= 1'b0;
        m_axi_arvalid_reg <= 1'b0;
    end else begin
        s_axi_arready_reg <= s_axi_arready_early;
        m_axi_arvalid_reg <= m_axi_arvalid_next;
    end

    // datapath
    if (store_axi_ar_input_to_output) begin
        m_axi_arid_reg <= s_axi_arid;
        m_axi_araddr_reg <= s_axi_araddr;
        m_axi_arlen_reg <= s_axi_arlen;
        m_axi_arsize_reg <= s_axi_arsize;
        m_axi_arburst_reg <= s_axi_arburst;
        m_axi_arlock_reg <= s_axi_arlock;
        m_axi_arcache_reg <= s_axi_arcache;
        m_axi_arprot_reg <= s_axi_arprot;
        m_axi_arqos_reg <= s_axi_arqos;
        m_axi_arregion_reg <= s_axi_arregion;
        m_axi_aruser_reg <= s_axi_aruser;
    end
end

end else begin

    // bypass AR channel
    assign m_axi_arid = s_axi_arid;
    assign m_axi_araddr = s_axi_araddr;
    assign m_axi_arlen = s_axi_arlen;
    assign m_axi_arsize = s_axi_arsize;
    assign m_axi_arburst = s_axi_arburst;
    assign m_axi_arlock = s_axi_arlock;
    assign m_axi_arcache = s_axi_arcache;
    assign m_axi_arprot = s_axi_arprot;
    assign m_axi_arqos = s_axi_arqos;
    assign m_axi_arregion = s_axi_arregion;
    assign m_axi_aruser = ARUSER_ENABLE ? s_axi_aruser : {ARUSER_WIDTH{1'b0}};
    assign m_axi_arvalid = s_axi_arvalid;
    assign s_axi_arready = m_axi_arready;

end

// R channel

if (R_REG_TYPE > 1) begin
// skid buffer, no bubble cycles

// datapath registers
reg                   m_axi_rready_reg = 1'b0;

reg [ID_WIDTH-1:0]    s_axi_rid_reg    = {ID_WIDTH{1'b0}};
reg [DATA_WIDTH-1:0]  s_axi_rdata_reg  = {DATA_WIDTH{1'b0}};
reg [1:0]             s_axi_rresp_reg  = 2'b0;
reg                   s_axi_rlast_reg  = 1'b0;
reg [RUSER_WIDTH-1:0] s_axi_ruser_reg  = {RUSER_WIDTH{1'b0}};
reg                   s_axi_rvalid_reg = 1'b0, s_axi_rvalid_next;

reg [ID_WIDTH-1:0]    temp_s_axi_rid_reg    = {ID_WIDTH{1'b0}};
reg [DATA_WIDTH-1:0]  temp_s_axi_rdata_reg  = {DATA_WIDTH{1'b0}};
reg [1:0]             temp_s_axi_rresp_reg  = 2'b0;
reg                   temp_s_axi_rlast_reg  = 1'b0;
reg [RUSER_WIDTH-1:0] temp_s_axi_ruser_reg  = {RUSER_WIDTH{1'b0}};
reg                   temp_s_axi_rvalid_reg = 1'b0, temp_s_axi_rvalid_next;

// datapath control
reg store_axi_r_input_to_output;
reg store_axi_r_input_to_temp;
reg store_axi_r_temp_to_output;

assign m_axi_rready = m_axi_rready_reg;

assign s_axi_rid    = s_axi_rid_reg;
assign s_axi_rdata  = s_axi_rdata_reg;
assign s_axi_rresp  = s_axi_rresp_reg;
assign s_axi_rlast  = s_axi_rlast_reg;
assign s_axi_ruser  = RUSER_ENABLE ? s_axi_ruser_reg : {RUSER_WIDTH{1'b0}};
assign s_axi_rvalid = s_axi_rvalid_reg;

// enable ready input next cycle if output is ready or the temp reg will not be filled on the next cycle (output reg empty or no input)
wire m_axi_rready_early = s_axi_rready | (~temp_s_axi_rvalid_reg & (~s_axi_rvalid_reg | ~m_axi_rvalid));

always @* begin
    // transfer sink ready state to source
    s_axi_rvalid_next = s_axi_rvalid_reg;
    temp_s_axi_rvalid_next = temp_s_axi_rvalid_reg;

    store_axi_r_input_to_output = 1'b0;
    store_axi_r_input_to_temp = 1'b0;
    store_axi_r_temp_to_output = 1'b0;

    if (m_axi_rready_reg) begin
        // input is ready
        if (s_axi_rready | ~s_axi_rvalid_reg) begin
            // output is ready or currently not valid, transfer data to output
            s_axi_rvalid_next = m_axi_rvalid;
            store_axi_r_input_to_output = 1'b1;
        end else begin
            // output is not ready, store input in temp
            temp_s_axi_rvalid_next = m_axi_rvalid;
            store_axi_r_input_to_temp = 1'b1;
        end
    end else if (s_axi_rready) begin
        // input is not ready, but output is ready
        s_axi_rvalid_next = temp_s_axi_rvalid_reg;
        temp_s_axi_rvalid_next = 1'b0;
        store_axi_r_temp_to_output = 1'b1;
    end
end

always @(posedge clk) begin
    if (rst) begin
        m_axi_rready_reg <= 1'b0;
        s_axi_rvalid_reg <= 1'b0;
        temp_s_axi_rvalid_reg <= 1'b0;
    end else begin
        m_axi_rready_reg <= m_axi_rready_early;
        s_axi_rvalid_reg <= s_axi_rvalid_next;
        temp_s_axi_rvalid_reg <= temp_s_axi_rvalid_next;
    end

    // datapath
    if (store_axi_r_input_to_output) begin
        s_axi_rid_reg   <= m_axi_rid;
        s_axi_rdata_reg <= m_axi_rdata;
        s_axi_rresp_reg <= m_axi_rresp;
        s_axi_rlast_reg <= m_axi_rlast;
        s_axi_ruser_reg <= m_axi_ruser;
    end else if (store_axi_r_temp_to_output) begin
        s_axi_rid_reg   <= temp_s_axi_rid_reg;
        s_axi_rdata_reg <= temp_s_axi_rdata_reg;
        s_axi_rresp_reg <= temp_s_axi_rresp_reg;
        s_axi_rlast_reg <= temp_s_axi_rlast_reg;
        s_axi_ruser_reg <= temp_s_axi_ruser_reg;
    end

    if (store_axi_r_input_to_temp) begin
        temp_s_axi_rid_reg   <= m_axi_rid;
        temp_s_axi_rdata_reg <= m_axi_rdata;
        temp_s_axi_rresp_reg <= m_axi_rresp;
        temp_s_axi_rlast_reg <= m_axi_rlast;
        temp_s_axi_ruser_reg <= m_axi_ruser;
    end
end

end else if (R_REG_TYPE == 1) begin
// simple register, inserts bubble cycles

// datapath registers
reg                   m_axi_rready_reg = 1'b0;

reg [ID_WIDTH-1:0]    s_axi_rid_reg    = {ID_WIDTH{1'b0}};
reg [DATA_WIDTH-1:0]  s_axi_rdata_reg  = {DATA_WIDTH{1'b0}};
reg [1:0]             s_axi_rresp_reg  = 2'b0;
reg                   s_axi_rlast_reg  = 1'b0;
reg [RUSER_WIDTH-1:0] s_axi_ruser_reg  = {RUSER_WIDTH{1'b0}};
reg                   s_axi_rvalid_reg = 1'b0, s_axi_rvalid_next;

// datapath control
reg store_axi_r_input_to_output;

assign m_axi_rready = m_axi_rready_reg;

assign s_axi_rid    = s_axi_rid_reg;
assign s_axi_rdata  = s_axi_rdata_reg;
assign s_axi_rresp  = s_axi_rresp_reg;
assign s_axi_rlast  = s_axi_rlast_reg;
assign s_axi_ruser  = RUSER_ENABLE ? s_axi_ruser_reg : {RUSER_WIDTH{1'b0}};
assign s_axi_rvalid = s_axi_rvalid_reg;

// enable ready input next cycle if output buffer will be empty
wire m_axi_rready_early = !s_axi_rvalid_next;

always @* begin
    // transfer sink ready state to source
    s_axi_rvalid_next = s_axi_rvalid_reg;

    store_axi_r_input_to_output = 1'b0;

    if (m_axi_rready_reg) begin
        s_axi_rvalid_next = m_axi_rvalid;
        store_axi_r_input_to_output = 1'b1;
    end else if (s_axi_rready) begin
        s_axi_rvalid_next = 1'b0;
    end
end

always @(posedge clk) begin
    if (rst) begin
        m_axi_rready_reg <= 1'b0;
        s_axi_rvalid_reg <= 1'b0;
    end else begin
        m_axi_rready_reg <= m_axi_rready_early;
        s_axi_rvalid_reg <= s_axi_rvalid_next;
    end

    // datapath
    if (store_axi_r_input_to_output) begin
        s_axi_rid_reg   <= m_axi_rid;
        s_axi_rdata_reg <= m_axi_rdata;
        s_axi_rresp_reg <= m_axi_rresp;
        s_axi_rlast_reg <= m_axi_rlast;
        s_axi_ruser_reg <= m_axi_ruser;
    end
end

end else begin

    // bypass R channel
    assign s_axi_rid = m_axi_rid;
    assign s_axi_rdata = m_axi_rdata;
    assign s_axi_rresp = m_axi_rresp;
    assign s_axi_rlast = m_axi_rlast;
    assign s_axi_ruser = RUSER_ENABLE ? m_axi_ruser : {RUSER_WIDTH{1'b0}};
    assign s_axi_rvalid = m_axi_rvalid;
    assign m_axi_rready = s_axi_rready;

end

endgenerate

endmodule
