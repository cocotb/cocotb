// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module trigger_counter (
    input logic i_clk,
    input logic i_rst_n,
    input logic i_trg,
    input logic i_valid,
    input logic [7:0] i_cnt,
    output logic o_pulse,
    output logic o_valid
);


  logic [7:0] cnt;

  always @(posedge i_clk or negedge i_rst_n) begin : p_seq_
    if (~i_rst_n) begin
      cnt <= 0;
      o_pulse <= 0;
      o_valid <= 0;
    end else begin
      o_pulse <= 0;
      o_valid <= i_valid;
      if (i_trg) begin
        cnt <= i_cnt;
      end else if (cnt != 0) begin
        cnt <= cnt - 1;
        o_pulse <= (cnt == 1) ? 1'b1 : 1'b0;
      end
    end
  end

endmodule
