-----------------------------------------------------------------------------------------
-- baud rate generator for uart 
--
-- this module has been changed to receive the baud rate dividing counter from registers.
-- the two registers should be calculated as follows:
-- first register:
--              baud_freq = 16*baud_rate / gcd(global_clock_freq, 16*baud_rate)
-- second register:
--              baud_limit = (global_clock_freq / gcd(global_clock_freq, 16*baud_rate)) - baud_freq 
--
-----------------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_unsigned.all;

entity baudGen is
  port ( clr       : in  std_logic;                     -- global reset input
         clk       : in  std_logic;                     -- global clock input
         -- baudFreq = 16 * baudRate / gcd(clkFreq, 16 * baudRate)
         baudFreq  : in  std_logic_vector(11 downto 0); -- baud rate setting registers - see header description
         -- baudLimit = clkFreq / gcd(clkFreq, 16 * baudRate) - baudFreq
         baudLimit : in  std_logic_vector(15 downto 0); -- baud rate setting registers - see header description
         ce16      : out std_logic);                    -- baud rate multiplyed by 16
end baudGen;

architecture Behavioral of baudGen is

  signal counter : std_logic_vector(15 downto 0);

  begin
    -- baud divider counter
    -- clock divider output
    process (clr, clk)
    begin
      if (clr = '1') then
        counter <= (others => '0');
        ce16 <= '0';
      elsif (rising_edge(clk)) then
        if (counter >= baudLimit) then
          counter <= counter - baudLimit;
          ce16 <= '1';
        else
          counter <= counter + baudFreq;
          ce16 <= '0';
        end if;
      end if;
    end process;
  end Behavioral;
