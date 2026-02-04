-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

--! Using 'ieee' libraries
library ieee;
use ieee.std_logic_1164.all;

entity debug_array is
    port (
        test_a : out std_logic_vector(3 downto 0);
        test_b : out std_logic_vector(3 downto 0)
    );
end debug_array;

architecture rtl of debug_array is
begin
    test_a <= (others => '0');
    test_b <= (others => '0');
end rtl;
