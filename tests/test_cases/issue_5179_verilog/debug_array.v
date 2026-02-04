// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module debug_array;

    reg [3:0] test_a;
    reg test_b_0;
    reg test_b_1;
    reg test_b_2;
    reg test_b_3;

    initial begin
        test_a   = 4'b0000;
        test_b_0 = 1'b0;
        test_b_1 = 1'b0;
        test_b_2 = 1'b0;
        test_b_3 = 1'b0;
    end

endmodule
