library ieee; use ieee.std_logic_1164.all;
              use ieee.numeric_std.all;

entity counter is
  generic (
    ENDVAL  : unsigned);
  port (
    clk     : in    std_logic;
    rst     : in    std_logic;
    enable  : in    std_logic;
    done    :   out std_logic);
end counter;

architecture rtl of counter is
  constant ZERO : unsigned(ENDVAL'range) := to_unsigned(0, ENDVAL'length);
  signal   cnt  : unsigned(ENDVAL'range);
begin
  c : process(clk)
  begin
    if (rising_edge(clk)) then
      if rst /= '0' then
        cnt <= ZERO;
      elsif ((enable = '1') and (cnt /= ENDVAL)) then
        cnt <= cnt + 1;
      end if;
    end if;
  end process c;

  d : process(clk)
  begin
    if (rising_edge(clk)) then
      if rst /= '0' then
        done <= '0';
      elsif (cnt = ENDVAL) then
        done <= '1';
      end if;
    end if;
  end process d;
end architecture rtl;
