-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

package test_vhdl_record_array_indexing_pack is

    type my_array_type is array (integer range <>, integer range <>) of integer;

    type top_record is record
        data : my_array_type(0 to 2 - 1, 0 to 5 - 1);
    end record;

end package test_vhdl_record_array_indexing_pack;

package body test_vhdl_record_array_indexing_pack is
end package body;

library ieee;
use ieee.std_logic_1164.all;

use work.test_vhdl_record_array_indexing_pack.all;

entity test_vhdl_record_array_indexing is
    port (
        pi_clk           : in std_logic;

        -- A record whose field is a 2-D array. Indexing this field triggers
        -- a special case in get_child_by_index, in particular in VHPI
        po_record_of_array   : out top_record
    );
end test_vhdl_record_array_indexing;

architecture rtl of test_vhdl_record_array_indexing is
begin
    process (pi_clk)
    begin
        if rising_edge(pi_clk) then
            po_record_of_array.data(0, 0) <= 42;
        end if;
    end process;
end rtl;
