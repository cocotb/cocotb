library ieee;
use ieee.std_logic_1164.all;

package uart2BusTop_pkg is

  component baudGen
    port (
      clr       : in  std_logic;
      clk       : in  std_logic;
      baudFreq  : in  std_logic_vector(11 downto 0);
      baudLimit : in  std_logic_vector(15 downto 0);
      ce16      : out std_logic);
  end component;

  component uartTx
    port (
      clr : in  std_logic;
      clk : in  std_logic;
      ce16 : in  std_logic;
      txData : in  std_logic_vector(7 downto 0);
      newTxData : in  std_logic;
      serOut : out  std_logic;
      txBusy : out  std_logic);
  end component;

  component uartRx
    port (
      clr       : in  std_logic;
      clk       : in  std_logic;
      ce16      : in  std_logic;
      serIn     : in  std_logic;
      rxData    : out std_logic_vector(7 downto 0);
      newRxData : out std_logic);
  end component;

  component uartTop
    port ( clr       : in  std_logic;
           clk       : in  std_logic;
           serIn     : in  std_logic;
           txData    : in  std_logic_vector(7 downto 0);
           newTxData : in  std_logic;
           baudFreq  : in  std_logic_vector(11 downto 0);
           baudLimit : in  std_logic_vector(15 downto 0);
           serOut    : out std_logic;
           txBusy    : out std_logic;
           rxData    : out std_logic_vector(7 downto 0);
           newRxData : out std_logic;
           baudClk   : out std_logic);
  end component;

  component uartParser
    generic ( AW : integer := 8);
    port ( clr        : in  std_logic;
           clk        : in  std_logic;
           txBusy     : in  std_logic;
           rxData     : in  std_logic_vector(7 downto 0);
           newRxData  : in  std_logic;
           intRdData  : in  std_logic_vector(7 downto 0);
           txData     : out std_logic_vector(7 downto 0);
           newTxData  : out std_logic;
           intReq     : out std_logic;
           intGnt     : in  std_logic;
           intAddress : out std_logic_vector(AW - 1 downto 0);
           intWrData  : out std_logic_vector(7 downto 0);
           intWrite   : out std_logic;
           intRead    : out std_logic);
  end component;

  component uart2BusTop
    generic
    (
      AW : integer := 8
    );
    port
    (
      clr          : in  std_logic;
      clk          : in  std_logic;
      serIn        : in  std_logic;
      serOut       : out std_logic;
      intAccessReq : out std_logic;
      intAccessGnt : in  std_logic;
      intRdData    : in  std_logic_vector(7 downto 0);
      intAddress   : out std_logic_vector(AW - 1 downto 0);
      intWrData    : out std_logic_vector(7 downto 0);
      intWrite     : out std_logic;
      intRead      : out std_logic
    );
  end component;

end uart2BusTop_pkg;
