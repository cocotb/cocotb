-- This file is public domain, it can be freely copied without restrictions.
-- SPDX-License-Identifier: CC0-1.0

library ieee;
use ieee.std_logic_1164.all;

entity tb is
end tb;

architecture structural of tb is
  signal period_ns  : real    := 10.0;
  signal start_high : boolean := true;
  signal clk        : std_ulogic;
begin

  clkgen_inst : entity work.clkgen
    port map (
      period_ns  => period_ns,
      start_high => start_high,
      clk        => clk);

  dut_inst : entity work.dut
    port map (
      clk => clk);

end structural;
