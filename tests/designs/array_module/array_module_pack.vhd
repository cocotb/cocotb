-- Copyright cocotb contributors
-- Copyright (c) 2016 Potential Ventures Ltd
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package array_module_pack is
    type t1 is array (0 to 3) of std_logic;
    type t2 is array (7 downto 4) of std_logic_vector(7 downto 0);
    type t3 is array (natural range <>) of std_logic_vector(7 downto 0);
    type t4 is array (0 to 3) of t2;
    type t5 is array (0 to 2, 0 to 3) of std_logic_vector(7 downto 0);
    type t6 is array (natural range <>, natural range <>) of std_logic_vector(7 downto 0);

    type rec_type is record
        a : std_logic;
        b : t3(0 to 2);
    end record rec_type;
    type     rec_array is array (natural range <>) of rec_type;
    constant REC_TYPE_ZERO  : rec_type  := ('0', (others=>(others=>'0')));
    constant REC_TYPE_ONE   : rec_type  := ('1', (others=>(others=>'1')));

end package array_module_pack;

package body array_module_pack is
end package body array_module_pack;
