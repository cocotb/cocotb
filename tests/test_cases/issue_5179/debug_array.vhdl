library ieee;
use ieee.std_logic_1164.all;

entity debug_array is
end entity;

architecture rtl of debug_array is
    signal test_a : std_logic_vector(3 downto 0);

    type std_logic_array is array(natural range <>) of std_logic;
    signal test_b : std_logic_array(3 downto 0);
begin
end architecture;
