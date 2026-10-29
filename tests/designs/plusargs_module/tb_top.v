// Copyright cocotb contributors
// Copyright (c) 2013 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause

module tb_top ;

    reg [1000:0] foo_string;
    integer result;

initial begin
    $display("SIM: Plusargs test");
    result = $value$plusargs("foo=%s", foo_string);
    $display("SIM: Plusarg foo has value %0s", foo_string);
    result = $value$plusargs("lol=%s", foo_string);
    $display("SIM: Plusarg lol has value %0s", foo_string);
    #1 $display("SIM: Test running");
end

endmodule //: tb_top
