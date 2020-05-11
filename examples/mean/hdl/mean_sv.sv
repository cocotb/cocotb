// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

//-----------------------------------------------------------------------------
//  sv wrapper for mean.vhd
//-----------------------------------------------------------------------------
import mean_pkg::*;


module mean_sv #(
  parameter  BUS_WIDTH=2)
  (
  input  logic        clk,
  input  logic        rst,
  input  logic        i_valid,
  input  t_data_array i_data [0:BUS_WIDTH-1],
  output logic        o_valid,
  output t_data       o_data
  );


// make constant from package visible
parameter DATA_WIDTH = c_data_width;

// VHDL DUT
  mean #(
    .BUS_WIDTH (BUS_WIDTH))
  mean (
    .clk      (clk),
    .rst      (rst),
    .i_valid  (i_valid),
    .i_data   (i_data),
    .o_valid  (o_valid),
    .o_data   (o_data)
    );


endmodule
