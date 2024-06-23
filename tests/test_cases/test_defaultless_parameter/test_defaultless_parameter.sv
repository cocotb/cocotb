// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module foo #(
    parameter int has_default = 7,
    parameter int has_no_default
) (
    input clk
);

endmodule

module cocotb_defaultless_parameter (
    input clk
);

    foo #(
        .has_default (2),
        .has_no_default (3))
    the_foo (
        .clk(clk)
    );

endmodule
