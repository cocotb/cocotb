// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module cocotb_package;
    // Necessary for Xcelium and Riviera in order for compiled packages to be visible
    import cocotb_package_pkg_1::*;
    import cocotb_package_pkg_2::*;

    parameter int seven_int = 7;
endmodule
