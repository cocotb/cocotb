// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module top (
    input logic x
);
  logic a, b;
  always @(x) a = x;
  always @(a) b = a;
  final if (b) $error("design was evaluated after vpi_finish");
endmodule
