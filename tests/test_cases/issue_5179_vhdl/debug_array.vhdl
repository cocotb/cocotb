-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

--! Using 'ieee' libraries
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity debug_array is
end entity debug_array;

architecture rtl of debug_array is

    signal test_a : std_logic_vector(3 downto 0);

    type std_logic_array is array(natural range <>) of std_logic;
    signal test_b : std_logic_array(3 downto 0);

begin
end architecture rtl;
