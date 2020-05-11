-- This file is public domain, it can be freely copied without restrictions.
-- SPDX-License-Identifier: CC0-1.0

-------------------------------------------------------------------------------
-- Package with constants, types & functions for mean.vhd
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;


package mean_pkg is

  constant C_DATA_WIDTH : natural := 6;

  subtype t_data is unsigned(C_DATA_WIDTH-1 downto 0);
  type t_data_array is array (natural range <>) of t_data;

  function clog2(n : positive) return natural;

end package;


package body mean_pkg is

  function clog2(n : positive) return natural is
  begin
    return integer(ceil(log2(real(n))));
  end function;

end package body;
