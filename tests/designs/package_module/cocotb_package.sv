// Necessary for at least Xcelium in order for compiled packages to be visible
import cocotb_package_pkg_1::*;
import cocotb_package_pkg_2::*;

module cocotb_package;
    parameter int seven_int = 7;
`ifndef __ICARUS__
    // NOCOMMIT -- can't properly access these parameters
    // is this known?  open separate issue?
    parameter logic [31:0] [3:0] packed_4567 = {
        32'd4,
        32'd5,
        32'd6,
        32'd7
    };
    parameter logic [31:0] unpacked_9876 [3:0] = {
        32'd9,
        32'd8,
        32'd7,
        32'd6
    };
`endif
endmodule
