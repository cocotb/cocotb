//-----------------------------------------------------------------------------
// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause
//-----------------------------------------------------------------------------

module test;

reg a, b;

always begin
    a <= 0;
    b <= 0;
    #10;
    a <= 1;
    b <= 1;
    #10;
end

endmodule
