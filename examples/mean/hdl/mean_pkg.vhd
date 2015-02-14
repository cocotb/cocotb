-------------------------------------------------------------------------------
-- Package with constants, types & functions for mean.vhd
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

    
package mean_pkg is

  constant DATA_WIDTH : natural := 6;
  
  subtype t_data is unsigned(DATA_WIDTH-1 downto 0);
  type t_data_array is array (natural range <>) of t_data;
  
  function clog2(n : positive) return natural;
  
end package;


package body mean_pkg is

  function clog2(n : positive) return natural is
  begin
    return integer(ceil(log2(real(n))));
  end function;
  
end package body;
