// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module unpacked_array_perf;
  parameter integer LEFT = 0;
  parameter integer RIGHT = 1023;
  reg [63:0] memory [LEFT:RIGHT];
  // Retain the otherwise unused memory in Icarus's compiled design.
  initial memory[LEFT] = 0;
endmodule
