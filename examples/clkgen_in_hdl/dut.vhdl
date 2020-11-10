-- This file is public domain, it can be freely copied without restrictions.
-- SPDX-License-Identifier: CC0-1.0

library ieee;
use ieee.std_logic_1164.all;

entity dut is
  port (
    signal rst_n : in std_ulogic := '0';
    signal clk   : in std_ulogic);
end dut;

architecture behavioral of dut is
  signal count : natural;
begin

  p_count : process (clk, rst_n)
  begin
    if rst_n = '0' then
      count <= 0;
    elsif rising_edge(clk) then
      count <= count + 1;
    end if;
  end process;

end behavioral;
