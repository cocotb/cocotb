-- Copyright cocotb contributors
-- Copyright (c) 2014 Potential Ventures Ltd
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause


library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package sample_module_package is

    type test_record is record
        a_in  : std_logic;
        b_out : std_logic;
    end record test_record;

end package sample_module_package;

package body sample_module_package is
end package body sample_module_package;
