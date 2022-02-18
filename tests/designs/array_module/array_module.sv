//-----------------------------------------------------------------------------
// Copyright (c) 2016 Potential Ventures Ltd
// Copyright (c) 2016 SolarFlare Communications Inc
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

typedef struct {
    logic a;
    logic [7:0] b[0:2];
} rec_type;

module array_module (
    input                                       clk,

    input  integer                              select_in,

    input          [7:0]                        port_desc_in,
    input          [0:7]                        port_asc_in,
    input          [1:8]                        port_ofst_in,

    output         [7:0]                        port_desc_out,
    output         [0:7]                        port_asc_out,
    output         [1:8]                        port_ofst_out,

    output logic                                port_logic_out,
    output logic   [7:0]                        port_logic_vec_out,
    //output bit                                  port_bool_out,
    //output integer                              port_int_out,
    //output real                                 port_real_out,
    //output byte                                 port_char_out,
    //output string                               port_str_out,
    output rec_type                             port_rec_out,
    output rec_type                             port_cmplx_out[0:1]
);

parameter logic          param_logic       = 1'b1;
parameter logic [7:0]    param_logic_vec   = 8'hDA;
//parameter bit            param_bool        = 1'b1;
//parameter integer        param_int         = 6;
//parameter real           param_real        = 3.14;
//parameter byte           param_char        = "p";
//parameter string         param_str         = "ARRAYMOD";
//parameter rec_type       param_rec         = '{a:'0, b:'{8'h00,8'h00,8'h00}}};
//parameter rec_type       param_cmplx [0:1] = '{'{a:'0, b:'{8'h00,8'h00,8'h00}}, '{a:'0, b:'{8'h00,8'h00,8'h00}}};

localparam logic          const_logic       = 1'b0;
localparam logic [7:0]    const_logic_vec   = 8'h3D;
//localparam bit            const_bool        = 1'b0;
//localparam integer        const_int         = 12;
//localparam real           const_real        = 6.28;
//localparam byte           const_char        = "c";
//localparam string         const_str         = "MODARRAY";
//localparam rec_type       const_rec         = '{a:'1, b:'{8'hFF,8'hFF,8'hFF}}};
//localparam rec_type       const_cmplx [1:2] = '{'{a:'1, b:'{8'hFF,8'hFF,8'hFF}}, '{a:'1, b:'{8'hFF,8'hFF,8'hFF}}};

wire [0:3]       sig_t1;
wire [7:0]       sig_t2[7:4];
wire [7:0]       sig_t3a[1:4];
wire [7:0]       sig_t3b[3:0];
wire [7:0]       sig_t4[0:3][7:4];
wire [7:0]       sig_t5[0:2][0:3];
wire [7:0]       sig_t6[0:1][2:4];

wire       [16:23]  sig_asc;
wire       [23:16]  sig_desc;
wire logic          sig_logic;
wire logic [7:0]    sig_logic_vec;
//     bit            sig_bool;
//     integer        sig_int;
//     real           sig_real;
//     byte           sig_char;
//     string         sig_str;
     rec_type       sig_rec;
     rec_type       sig_cmplx [0:1];

typedef logic [7:0] uint16_t;

uint16_t sig_t7 [3:0][3:0];
uint16_t [3:0][3:0] sig_t8;

assign port_ofst_out = port_ofst_in;

//assign port_rec_out       = (select_in == 1) ? const_rec       : (select_in == 2) ? sig_rec       : param_rec;
//assign port_cmplx_out     = (select_in == 1) ? const_cmplx     : (select_in == 2) ? sig_cmplx     : param_cmplx;

always @(posedge clk) begin
    if (select_in == 1) begin
        port_logic_out         = const_logic;
        port_logic_vec_out     = const_logic_vec;
//        port_bool_out          = const_bool;
//        port_int_out           = const_int;
//        port_real_out          = const_real;
//        port_char_out          = const_char;
//        port_str_out           = const_str;
        port_rec_out.a         = sig_rec.a;
        port_rec_out.b[0]      = sig_rec.b[0];
        port_rec_out.b[1]      = sig_rec.b[1];
        port_rec_out.b[2]      = sig_rec.b[2];
        port_cmplx_out[0].a    = sig_cmplx[0].a;
        port_cmplx_out[0].b[0] = sig_cmplx[0].b[0];
        port_cmplx_out[0].b[1] = sig_cmplx[0].b[1];
        port_cmplx_out[0].b[2] = sig_cmplx[0].b[2];
        port_cmplx_out[1].a    = sig_cmplx[1].a;
        port_cmplx_out[1].b[0] = sig_cmplx[1].b[0];
        port_cmplx_out[1].b[1] = sig_cmplx[1].b[1];
        port_cmplx_out[1].b[2] = sig_cmplx[1].b[2];
    end else begin
        if (select_in == 2) begin
            port_logic_out         = sig_logic;
            port_logic_vec_out     = sig_logic_vec;
//            port_bool_out          = sig_bool;
//            port_int_out           = sig_int;
//            port_real_out          = sig_real;
//            port_char_out          = sig_char;
//            port_str_out           = sig_str;
            port_rec_out.a         = sig_rec.a;
            port_rec_out.b[0]      = sig_rec.b[0];
            port_rec_out.b[1]      = sig_rec.b[1];
            port_rec_out.b[2]      = sig_rec.b[2];
            port_cmplx_out[0].a    = sig_cmplx[0].a;
            port_cmplx_out[0].b[0] = sig_cmplx[0].b[0];
            port_cmplx_out[0].b[1] = sig_cmplx[0].b[1];
            port_cmplx_out[0].b[2] = sig_cmplx[0].b[2];
            port_cmplx_out[1].a    = sig_cmplx[1].a;
            port_cmplx_out[1].b[0] = sig_cmplx[1].b[0];
            port_cmplx_out[1].b[1] = sig_cmplx[1].b[1];
            port_cmplx_out[1].b[2] = sig_cmplx[1].b[2];
        end else begin
            port_logic_out         = param_logic;
            port_logic_vec_out     = param_logic_vec;
//            port_bool_out          = param_bool;
//            port_int_out           = param_int;
//            port_real_out          = param_real;
//            port_char_out          = param_char;
//            port_str_out           = param_str;
            port_rec_out.a         = sig_rec.a;
            port_rec_out.b[0]      = sig_rec.b[0];
            port_rec_out.b[1]      = sig_rec.b[1];
            port_rec_out.b[2]      = sig_rec.b[2];
            port_cmplx_out[0].a    = sig_cmplx[0].a;
            port_cmplx_out[0].b[0] = sig_cmplx[0].b[0];
            port_cmplx_out[0].b[1] = sig_cmplx[0].b[1];
            port_cmplx_out[0].b[2] = sig_cmplx[0].b[2];
            port_cmplx_out[1].a    = sig_cmplx[1].a;
            port_cmplx_out[1].b[0] = sig_cmplx[1].b[0];
            port_cmplx_out[1].b[1] = sig_cmplx[1].b[1];
            port_cmplx_out[1].b[2] = sig_cmplx[1].b[2];
        end
    end
end

genvar idx1;
generate
for (idx1 = 16; idx1 <= 23; idx1=idx1+1) begin:asc_gen
    localparam OFFSET = 16-0;
    reg sig;
    always @(posedge clk) begin
        sig <= port_asc_in[idx1-OFFSET];
    end
    assign sig_asc[idx1] = sig;
    assign port_asc_out[idx1-OFFSET] = sig_asc[idx1];
end
endgenerate

genvar idx2;
generate
for (idx2 = 7; idx2 >= 0; idx2=idx2-1) begin:desc_gen
    localparam OFFSET = 23-7;
    reg sig;
    always @(posedge clk) begin
        sig <= port_desc_in[idx2];
    end
    assign sig_desc[idx2+OFFSET] = sig;
    assign port_desc_out[idx2] = sig_desc[idx2+OFFSET];
end
endgenerate

endmodule
