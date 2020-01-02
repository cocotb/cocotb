library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_top is
end;

architecture impl of tb_top is
    signal dummy_sig : std_logic := '0';
begin
    process
    begin
        wait for 10 ns;
        dummy_sig <= '1';
    end process;
end architecture;
