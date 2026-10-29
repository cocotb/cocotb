// Copyright cocotb contributors
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

`ifndef NOTIMESCALE
`timescale 1 ps / 1 ps
`endif  // `ifndef NOTIMESCALE

module sample_module_1 #(
    parameter int EXAMPLE_WIDTH
)(
    input logic clk,
    input logic rst,
    input logic [EXAMPLE_WIDTH:0] stream_in_data,
    input logic stream_in_valid,
    output logic stream_in_ready,
    output logic [EXAMPLE_WIDTH:0] stream_out_data,
    output logic stream_out_valid,
    input logic stream_out_ready
);

    initial begin
        stream_in_ready  = 1'b0;
        stream_out_valid = 1'b0;
        stream_out_data  = 16'h0000;
    end

    always_ff @(posedge clk or posedge rst) begin
        if (rst) begin
            stream_in_ready  <= 1'b0;
            stream_out_valid <= 1'b0;
            stream_out_data  <= 16'h0000;
        end else begin
            stream_in_ready  <= 1'b1;
            if (stream_in_valid && stream_in_ready) begin
                stream_out_data  <= stream_in_data + 16'h0001;
                stream_out_valid <= 1'b1;
            end
            if (stream_out_valid && stream_out_ready) begin
                stream_out_valid <= 1'b0;
            end
        end
    end
endmodule : sample_module_1
