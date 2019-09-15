// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

`timescale 1 ps / 1 ps

module module_a (
    input clk,
    input [31:0] data_in,
    output reg [31:0] data_out);

always @ (posedge clk)
begin
    data_out <= data_in + 2;
end

endmodule

module module_b (
    input clk,
    input [31:0] data_in,
    output reg [31:0] data_out
);

always @ (posedge clk)
begin
    data_out <= data_in + 5;
end

endmodule

module basic_hierarchy_module (
    input clk,
    input reset
);

reg [31:0] counter;

always @ (posedge clk or negedge reset)
begin
    if (~reset) begin
        counter <= 0;
    end else begin
        counter <= counter + 1;
    end
end

wire [31:0] counter_plus_two;
wire [31:0] counter_plus_five;

module_a i_module_a (
    .clk        (clk),
    .data_in    (counter),
    .data_out   (counter_plus_two)
);

module_b i_module_b (
    .clk        (clk),
    .data_in    (counter),
    .data_out   (counter_plus_five)
);

endmodule
