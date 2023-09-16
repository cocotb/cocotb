// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

`ifdef VERILATOR  // make parameter readable from VPI
  `define VL_RD /*verilator public_flat_rd*/
`else
  `define VL_RD
`endif

// D Flip Flop
module dff8 #(
    parameter int DATA_WIDTH `VL_RD = 8, // Data width in bits

    // "Input Offset"
    // Instead of 8 downto 0 use 11 downto 3
    parameter int IOFF `VL_RD = 3,

    // "Output Offset"
    // Instead of 8 downto 0 use 13 downto 5
    parameter int OOFF `VL_RD = 5
) (
    input clk_i,
    input rst_i, // asynchronous reset

    // Little endian: d_i[7] is the most significant bit
    input [DATA_WIDTH-1+IOFF:0+IOFF] d_i, // Input
    output logic [DATA_WIDTH-1+OOFF:0+OOFF] q_o, // Output
    output logic [DATA_WIDTH-1+OOFF:0+OOFF] nq_o, // Negative output

    // Big endian (BE): be_d_i[0] is the most significant bit
    input [0+IOFF:DATA_WIDTH-1+IOFF] be_d_i, // Input
    output logic [0+OOFF:DATA_WIDTH-1+OOFF] be_q_o, // Output
    output logic [0+OOFF:DATA_WIDTH-1+OOFF] be_nq_o // Negative output
    );

    // Little Endian
    logic [DATA_WIDTH-1:0] q_w;
    always @(posedge clk_i, posedge rst_i) begin : proc_le_reg
        if (rst_i == 1'b1) begin
            q_w <= {DATA_WIDTH{1'b0}};
        end else begin
            q_w <= d_i;
        end
    end
    assign nq_o = ~q_w;
    assign q_o = q_w;

    // Big Endian
    logic [DATA_WIDTH-1:0] be_q_w;
    always @(posedge clk_i, posedge rst_i) begin : proc_be_reg
        if (rst_i == 1'b1) begin
            be_q_w <= {DATA_WIDTH{1'b0}};
        end else begin
            be_q_w <= be_d_i;
        end
    end
    assign be_nq_o = ~be_q_w;
    assign be_q_o = be_q_w;

endmodule
