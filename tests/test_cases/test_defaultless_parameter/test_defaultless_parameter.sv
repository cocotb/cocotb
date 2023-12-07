// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module foo #(
    parameter int has_default = 7,
    parameter int has_no_default
) ();

endmodule

module cocotb_defaultless_parameter;

    foo #(
        .has_default (2),
        .has_no_default (3))
    the_foo ();

endmodule
