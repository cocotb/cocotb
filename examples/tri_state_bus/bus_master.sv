// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

`timescale 1ns/1ps

// Drives an 8-bit bus while `drive_en` is high and leaves it floating otherwise, so the bus can be
// used by someone else in between.
module bus_master (
    inout  wire [7:0] data_bus,
    input  wire       drive_en,
    input  wire [7:0] data_out,
    output wire [7:0] data_in
);
    assign data_bus = drive_en ? data_out : 8'hzz;
    assign data_in  = data_bus;
endmodule
