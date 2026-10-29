// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

`timescale 1us/1us

module test (output [15:0] o);

  genvar idx1;
  generate for (idx1 = 0; idx1 < 10; idx1 = idx1 + 1)
    begin: foobar
      assign o[idx1] = 1;
    end
  endgenerate

  genvar idx2;
  generate for (idx2 = 10; idx2 < 16; idx2 = idx2 + 1)
    begin: foo   // Should not be confused with "foobar" which shares the same prefix
      assign o[idx2] = 1;
    end
  endgenerate

endmodule
