-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library ieee;
    use ieee.std_logic_1164.all;

entity myentity is
    port (
        clk     : in    std_logic;
        a_data  : in    std_logic_vector(31 downto 0);
        b_data  :   out std_logic_vector(31 downto 0));
end entity myentity;

architecture rtl of myentity is
begin

    process (clk) is
    begin
        if (rising_edge(clk)) then
            b_data <= a_data;
        end if;
    end process;

end architecture rtl;
