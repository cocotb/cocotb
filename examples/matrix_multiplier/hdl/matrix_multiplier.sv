// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

// Matrix Multiplier DUT
`timescale 1ns/1ps

`ifdef VERILATOR  // make parameter readable from VPI
  `define VL_RD /*verilator public_flat_rd*/
`else  // `ifdef VERILATOR
  `define VL_RD
`endif  // `ifdef VERILATOR

module matrix_multiplier #(
  parameter int DATA_WIDTH `VL_RD = 8,
  parameter int A_ROWS `VL_RD = 8,
  parameter int B_COLUMNS `VL_RD = 5,
  parameter int A_COLUMNS_B_ROWS `VL_RD = 4,
  parameter int C_DATA_WIDTH = (2 * DATA_WIDTH) + $clog2(A_COLUMNS_B_ROWS)
) (
  input                           clk_i,
  input                           reset_i,
  input                           valid_i,
  output logic                    valid_o,
  input        [DATA_WIDTH-1:0]   a_i[0:A_ROWS*A_COLUMNS_B_ROWS-1],
  input        [DATA_WIDTH-1:0]   b_i[0:A_COLUMNS_B_ROWS*B_COLUMNS-1],
  output logic [C_DATA_WIDTH-1:0] c_o[0:A_ROWS*B_COLUMNS-1]
);

  logic [C_DATA_WIDTH-1:0] c_calc[A_ROWS * B_COLUMNS];

  always @(*) begin : multiply
    logic [C_DATA_WIDTH-1:0] c_element;
    for (int i = 0; i < A_ROWS; i = i + 1) begin : C_ROWS
      for (int j = 0; j < B_COLUMNS; j = j + 1) begin : C_COLUMNS
        c_element = 0;
        for (int k = 0; k < A_COLUMNS_B_ROWS; k = k + 1) begin : DOT_PRODUCT
          c_element = c_element + (a_i[(i * A_COLUMNS_B_ROWS) + k] * b_i[(k * B_COLUMNS) + j]);
        end
        c_calc[(i * B_COLUMNS) + j] = c_element;
      end
    end
  end

  always @(posedge clk_i) begin : proc_reg
    if (reset_i) begin
      valid_o <= 1'b0;

      for (int idx = 0; idx < (A_ROWS * B_COLUMNS); idx++) begin
        c_o[idx] <= '0;
      end
    end else begin
      valid_o <= valid_i;

      for (int idx = 0; idx < (A_ROWS * B_COLUMNS); idx++) begin
        c_o[idx] <= c_calc[idx];
      end
    end
  end

endmodule
