-- This file is public domain, it can be freely copied without restrictions.
-- SPDX-License-Identifier: CC0-1.0

library ieee;
use ieee.std_logic_1164.all;

entity clkgen is
  port(
    period_ns  : in  real    := 10.0;
    start_high : in  boolean := true;
    clk        : out std_ulogic);
end clkgen;

architecture behavioral of clkgen is
  signal clk_int : std_ulogic;
begin
  process
  begin
    if start_high then
      clk_int <= '1';
    else
      clk_int <= '0';
    end if;
    while true loop
      wait for 0.5 * period_ns * 1 ns;
      clk_int <= not clk_int;
    end loop;
  end process;

  clk <= clk_int;

end behavioral;
