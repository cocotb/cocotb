-- This file is public domain, it can be freely copied without restrictions.
-- SPDX-License-Identifier: CC0-1.0

-------------------------------------------------------------------------------
-- Calculates mean of data input bus
-------------------------------------------------------------------------------
library ieee ;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.mean_pkg.all;


entity mean is
generic (
  BUS_WIDTH : natural := 4);
port (
  clk      : in  std_logic;
  rst      : in  std_logic;
  i_valid  : in  std_logic;
  i_data   : in  t_data_array(0 to BUS_WIDTH-1);
  o_valid  : out std_logic;
  o_data   : out t_data
  );
end mean;


architecture RTL of mean is

  constant DATA_WIDTH : natural := C_DATA_WIDTH;
  constant SUM_WIDTH  : natural := DATA_WIDTH + clog2(BUS_WIDTH);
--  constant SUM_WIDTH : natural := DATA_WIDTH + clog2(BUS_WIDTH) - 1;  -- introduce bug

  signal s_sum : unsigned(SUM_WIDTH-1 downto 0) := (others => '0');
  signal s_valid : std_logic := '0';

begin

  assert BUS_WIDTH = 2**(clog2(BUS_WIDTH))
    report LF & "   BUS_WIDTH = " & integer'image(BUS_WIDTH) & " , should be a power of 2!"
    severity Failure;


  process(clk)
    variable v_sum : unsigned(s_sum'range);
  begin
    if rising_edge(clk) then
      s_valid <= i_valid;

      if i_valid = '1' then
        v_sum := (others => '0');
        for i in i_data'range loop
          v_sum := v_sum + resize(i_data(i), v_sum'length);
        end loop;

        s_sum <= v_sum;
      end if;

      if rst = '1' then
        s_sum <= (others => '0');
        s_valid <= '0';
      end if;
    end if;
  end process;

  o_valid <= s_valid;
  o_data <= resize(shift_right(s_sum, clog2(BUS_WIDTH)), o_data'length);

end rtl;
