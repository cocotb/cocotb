-- This file is public domain, it can be freely copied without restrictions.
-- SPDX-License-Identifier: CC0-1.0

-- Matrix Multiplier DUT
library ieee ;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.matrix_multiplier_pkg.all;

entity matrix_multiplier is
  generic (
    DATA_WIDTH : positive := 8;
    A_ROWS : positive := 8;
    B_COLUMNS : positive := 5;
    A_COLUMNS_B_ROWS : positive := 4
  );
  port (
    clk_i   : in    std_logic;
    reset_i : in    std_logic;
    valid_i : in    std_logic;
    valid_o : out   std_logic;
    a_i     : in    flat_matrix_type(0 to (A_ROWS * A_COLUMNS_B_ROWS) - 1)(DATA_WIDTH - 1 downto 0);
    b_i     : in    flat_matrix_type(0 to (A_COLUMNS_B_ROWS * B_COLUMNS) - 1)(DATA_WIDTH - 1 downto 0);
    c_o     : out   flat_matrix_type(0 to (A_ROWS * B_COLUMNS) - 1)((2 * DATA_WIDTH) + clog2(A_COLUMNS_B_ROWS) - 1 downto 0)
  );
end entity matrix_multiplier;

architecture rtl of matrix_multiplier is

  signal c_calc : flat_matrix_type(c_o'RANGE)(c_o(0)'RANGE);

begin

  multiply : process (all) is

    variable c_var : flat_matrix_type(c_o'RANGE)(c_o(0)'RANGE);

  begin

    c_var := (others => (others => '0'));

    C_ROWS : for i in 0 to A_ROWS-1 loop
      C_COLUMNS : for j in 0 to B_COLUMNS-1 loop
        DOT_PRODUCT : for k in 0 to A_COLUMNS_B_ROWS-1 loop
          c_var((i * B_COLUMNS) + j) := c_var((i * B_COLUMNS) + j) + (a_i((i * A_COLUMNS_B_ROWS) + k) * b_i((k * B_COLUMNS) + j));
        end loop;
      end loop;
    end loop;

    c_calc <= c_var;

  end process multiply;

  proc_reg : process (clk_i) is
  begin

    if (rising_edge(clk_i)) then
      if (reset_i) then
        valid_o <= '0';
        c_o <= (others => (others => '0'));
      else
        valid_o <= valid_i;

        if (valid_i) then
          c_o <= c_calc;
        else
          c_o <= (others => (others => 'X'));
        end if;
      end if;
    end if;

  end process proc_reg;

end architecture rtl;
