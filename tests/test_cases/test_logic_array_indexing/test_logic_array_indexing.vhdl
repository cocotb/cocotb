-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

--! Using 'ieee' libraries
library ieee;
use ieee.std_logic_1164.all;

entity test_logic_array_indexing is
    port (
        test_a : out std_logic_vector(3 downto 0);
        test_b : out std_logic_vector(3 downto 0)
    );
end test_logic_array_indexing;

architecture rtl of test_logic_array_indexing is
begin

    process
    begin
        test_a <= (others => '0');
        test_b <= (others => '0');

        wait for 10 ns;

        test_a(0) <= '1';

        wait;
    end process;

end rtl;
