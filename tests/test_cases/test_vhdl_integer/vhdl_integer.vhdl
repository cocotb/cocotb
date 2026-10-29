-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library ieee;
use ieee.std_logic_1164.all;

entity vhdl_integer is
  port(
    i_int : in  integer;
    o_int : out integer
  );
end entity vhdl_integer;

architecture RTL of vhdl_integer is
  signal s_int : integer := 0;

  type ints is record
    a : integer;
    b : integer;
  end record ints;

  signal s_ints : ints := (1, 2);
begin

  process
  begin
    wait for 10 ns;
    s_int <= s_int + 1;
    s_ints.a <= s_ints.a + 1;
    s_ints.b <= s_ints.b + 1;

  end process;

  o_int <= transport i_int after 10 ns;

end architecture RTL;
