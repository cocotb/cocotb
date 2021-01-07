library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package array_types is
    type io_array is array (0 to 1) of std_logic_vector(7 downto 0);
end package array_types;

library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.array_types.all;

entity array_buses is
    port (
        clk        : in  std_logic;
        in_data    : in  io_array;
        in_valid   : in  std_logic_vector(0 to 1);
        out_data   : out io_array;
        out_valid  : out std_logic_vector(0 to 1)
    );
end;

architecture impl of array_buses is
    signal tmp_data: io_array := (others => (others => '0'));
    signal tmp_valid: std_logic_vector(0 to 1) := (others => '0');
begin
    process (clk)
    begin
        if (rising_edge(clk)) then
            tmp_data <= in_data;
            tmp_valid <= in_valid;
        end if;
    end process;

   out_data(0) <= tmp_data(0);
   out_data(1) <= tmp_data(1);
   out_valid(0) <= tmp_valid(0);
   out_valid(1) <= tmp_valid(1);

end architecture;
