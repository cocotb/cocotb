library ieee; use ieee.std_logic_1164.all;
              use ieee.numeric_std.all;
library work;

entity counters is
  port (
    clk     : in    std_logic;
    rst     : in    std_logic;
    enable  : in    std_logic;
    done    :   out std_logic_vector(3 downto 0));
end counters;

architecture rtl of counters is
  constant INSTALL     : boolean := TRUE;
  constant COUNTER_LEN : natural := 8;
begin
  install_gen : if (INSTALL) generate
  begin
    cntr : for i in done'range generate
      constant ENDVAL : unsigned(COUNTER_LEN-1 downto 0) := to_unsigned(2*(i+1), COUNTER_LEN);
    begin
      c_i : entity work.counter(rtl)
        generic map (
          ENDVAL => ENDVAL)
        port map(
          clk    => clk,
          rst    => rst,
          enable => enable,
          done   => done(i));
    end generate cntr;
  end generate install_gen;
end architecture rtl;
