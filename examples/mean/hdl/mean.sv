// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

//-----------------------------------------------------------------------------
// Calculates mean of data input bus
//-----------------------------------------------------------------------------

`timescale 1ns/1ps


module mean #(
  parameter int BUS_WIDTH = 4,
  parameter int DATA_WIDTH = 6
) (
  input  logic                  clk,
  input  logic                  rst,
  input  logic                  i_valid,
  input  logic [DATA_WIDTH-1:0] i_data [0:BUS_WIDTH-1],
  output logic                  o_valid,
  output logic [DATA_WIDTH-1:0] o_data
  );


  localparam int SUM_WIDTH = DATA_WIDTH + $clog2(BUS_WIDTH);
//  localparam int SUM_WIDTH = DATA_WIDTH + $clog2(BUS_WIDTH) - 1;  // introduce bug

  logic [SUM_WIDTH-1:0] v_sum;
  logic [SUM_WIDTH-1:0] s_sum;
  logic s_valid;

  initial begin
    if (BUS_WIDTH != 2**($clog2(BUS_WIDTH))) begin
      $fatal(1, "parameter BUS_WIDTH should be a power of 2!");
    end
  end


  always @* begin
    v_sum = '0;

    for (int i = 0; i < BUS_WIDTH; i++) begin
      v_sum = v_sum + i_data[i];
    end
  end

  always @(posedge clk) begin
    s_valid <= i_valid;

    if (i_valid) begin
      s_sum <= v_sum;
    end

    if (rst) begin
      s_sum <= '0;
      s_valid <= 1'b0;
    end
  end

  assign o_valid = s_valid;
  assign o_data = s_sum >> $clog2(BUS_WIDTH);


  initial begin
    int idx;
    $dumpfile("dump.vcd");
    $dumpvars(0, mean);
    for (idx = 0; idx < BUS_WIDTH; idx++)
        $dumpvars(0, i_data[idx]);
    #1;
  end

endmodule
