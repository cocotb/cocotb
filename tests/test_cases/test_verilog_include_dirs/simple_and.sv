// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause
`include "a.vh"
`include "b.vh"
`include "c.vh"

module simple_and (
    input [`DATA_BYTES-1:0]               a,
    input [`DATA_WIDTH+2:0]               b,
    output [`DATA_LAST+4:0]               c
);

assign c = a & b;

endmodule
