-----------------------------------------------------------------------------------------
-- uart top level module  
--
-----------------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

library work;
use work.uart2BusTop_pkg.all;

entity uartTop is
  port ( -- global signals
         clr       : in  std_logic;                     -- global reset input
         clk       : in  std_logic;                     -- global clock input
         -- uart serial signals
         serIn     : in  std_logic;                     -- serial data input
         serOut    : out std_logic;                     -- serial data output
         -- transmit and receive internal interface signals
         txData    : in  std_logic_vector(7 downto 0);  -- data byte to transmit
         newTxData : in  std_logic;                     -- asserted to indicate that there is a new data byte for transmission
         txBusy    : out std_logic;                     -- signs that transmitter is busy
         rxData    : out std_logic_vector(7 downto 0);  -- data byte received
         newRxData : out std_logic;                     -- signs that a new byte was received
         -- baud rate configuration register - see baudGen.vhd for details
         baudFreq  : in  std_logic_vector(11 downto 0); -- baud rate setting registers - see header description
         baudLimit : in  std_logic_vector(15 downto 0); -- baud rate setting registers - see header description
         baudClk   : out std_logic);                    -- 
end uartTop;

architecture Behavioral of uartTop is

  signal ce16 : std_logic; -- clock enable at bit rate

  begin
    -- baud rate generator module
    bg : baudGen
      port map (
        clr => clr,
        clk => clk,
        baudFreq => baudFreq,
        baudLimit => baudLimit,
        ce16 => ce16);
    -- uart receiver
    ut : uartTx
      port map (
        clr => clr,
        clk => clk,
        ce16 => ce16,
        txData => txData,
        newTxData => newTxData,
        serOut => serOut,
        txBusy => txBusy);
    -- uart transmitter
    ur : uartRx
      port map (
        clr => clr,
        clk => clk,
        ce16 => ce16,
        serIn => serIn,
        rxData => rxData,
        newRxData => newRxData);
    baudClk <= ce16;
  end Behavioral;
