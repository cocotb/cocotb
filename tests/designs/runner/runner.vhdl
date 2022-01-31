-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity runner is
generic(
    WIDTH_IN : integer := 4;
    WIDTH_OUT : integer := 8);
port(
    data_in : in signed(WIDTH_IN-1 downto 0);
    data_out : out signed(WIDTH_OUT-1 downto 0));
end entity;

architecture rtl of runner is
begin

end architecture;
