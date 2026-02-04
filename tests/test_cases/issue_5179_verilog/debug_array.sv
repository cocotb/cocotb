// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module debug_array();

    logic [3:0] test_a;
    logic test_b [3:0];

    initial begin
        test_a = 4'b0000;
        test_b[0] = 1'b0;
        test_b[1] = 1'b0;
        test_b[2] = 1'b0;
        test_b[3] = 1'b0;
    end

endmodule
