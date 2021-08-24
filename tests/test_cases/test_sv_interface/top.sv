// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

`timescale 1us/1us

interface sv_if();
  logic a;
  reg b;
  wire c;
endinterface

module top (
  input x,
  output y
);

sv_if sv_if_i();

endmodule
