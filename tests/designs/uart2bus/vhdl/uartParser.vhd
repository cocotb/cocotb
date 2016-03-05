-----------------------------------------------------------------------------------------
-- uart parser module  
--
-----------------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.ALL;
use ieee.std_logic_unsigned.ALL;

entity uartParser is
  generic ( -- parameters 
            AW : integer := 8);
  port ( -- global signals 
         clr        : in  std_logic;                         -- global reset input
         clk        : in  std_logic;                         -- global clock input
	 -- transmit and receive internal interface signals from uart interface
         txBusy     : in  std_logic;                         -- signs that transmitter is busy
         rxData     : in  std_logic_vector(7 downto 0);      -- data byte received
         newRxData  : in  std_logic;                         -- signs that a new byte was received
         txData     : out std_logic_vector(7 downto 0);      -- data byte to transmit
         newTxData  : out std_logic;                         -- asserted to indicate that there is a new data byte for transmission
	 -- internal bus to register file 
         intReq     : out std_logic;                         -- 
         intGnt     : in  std_logic;                         -- 
         intRdData  : in  std_logic_vector(7 downto 0);      -- data read from register file
         intAddress : out std_logic_vector(AW - 1 downto 0); -- address bus to register file
         intWrData  : out std_logic_vector(7 downto 0);      -- write data to register file
         intWrite   : out std_logic;                         -- write control to register file
         intRead    : out std_logic);                        -- read control to register file
end uartParser;

architecture Behavioral of uartParser is

  -- internal constants 
  -- main (receive) state machine states
  signal   mainSm         : std_logic_vector(3 downto 0); -- main state machine
  constant mainIdle       : std_logic_vector(mainSm'range) := "0000";
  constant mainWhite1     : std_logic_vector(mainSm'range) := "0001";
  constant mainData       : std_logic_vector(mainSm'range) := "0010";
  constant mainWhite2     : std_logic_vector(mainSm'range) := "0011";
  constant mainAddr       : std_logic_vector(mainSm'range) := "0100";
  constant mainEol        : std_logic_vector(mainSm'range) := "0101";
  -- binary mode extension states
  constant mainBinCmd     : std_logic_vector(mainSm'range) := "1000";
  constant mainBinAdrh    : std_logic_vector(mainSm'range) := "1001";
  constant mainBinAdrl    : std_logic_vector(mainSm'range) := "1010";
  constant mainBinLen     : std_logic_vector(mainSm'range) := "1011";
  constant mainBinData    : std_logic_vector(mainSm'range) := "1100";
  
  -- transmit state machine
  signal   txSm           : std_logic_vector(2 downto 0); -- transmit state machine
  constant txIdle         : std_logic_vector(txSm'range) := "000";
  constant txHiNib        : std_logic_vector(txSm'range) := "001";
  constant txLoNib        : std_logic_vector(txSm'range) := "100";
  constant txCharCR       : std_logic_vector(txSm'range) := "101";
  constant txCharLF       : std_logic_vector(txSm'range) := "110";

  -- define characters used by the parser
  constant charNul        : std_logic_vector(7 downto 0) := x"00";
  constant charTab        : std_logic_vector(7 downto 0) := x"09";
  constant charLF         : std_logic_vector(7 downto 0) := x"0A";
  constant charCR         : std_logic_vector(7 downto 0) := x"0D";
  constant charSpace      : std_logic_vector(7 downto 0) := x"20";
  constant charZero       : std_logic_vector(7 downto 0) := x"30";
  constant charOne        : std_logic_vector(7 downto 0) := x"31";
  constant charTwo        : std_logic_vector(7 downto 0) := x"32";
  constant charThree      : std_logic_vector(7 downto 0) := x"33";
  constant charFour       : std_logic_vector(7 downto 0) := x"34";
  constant charFive       : std_logic_vector(7 downto 0) := x"35";
  constant charSix        : std_logic_vector(7 downto 0) := x"36";
  constant charSeven      : std_logic_vector(7 downto 0) := x"37";
  constant charEight      : std_logic_vector(7 downto 0) := x"38";
  constant charNine       : std_logic_vector(7 downto 0) := x"39";
  constant charAHigh      : std_logic_vector(7 downto 0) := x"41";
  constant charBHigh      : std_logic_vector(7 downto 0) := x"42";
  constant charCHigh      : std_logic_vector(7 downto 0) := x"43";
  constant charDHigh      : std_logic_vector(7 downto 0) := x"44";
  constant charEHigh      : std_logic_vector(7 downto 0) := x"45";
  constant charFHigh      : std_logic_vector(7 downto 0) := x"46";
  constant charRHigh      : std_logic_vector(7 downto 0) := x"52";
  constant charWHigh      : std_logic_vector(7 downto 0) := x"57";
  constant charALow       : std_logic_vector(7 downto 0) := x"61";
  constant charBLow       : std_logic_vector(7 downto 0) := x"62";
  constant charCLow       : std_logic_vector(7 downto 0) := x"63";
  constant charDLow       : std_logic_vector(7 downto 0) := x"64";
  constant charELow       : std_logic_vector(7 downto 0) := x"65";
  constant charFLow       : std_logic_vector(7 downto 0) := x"66";
  constant charRLow       : std_logic_vector(7 downto 0) := x"72";
  constant charWLow       : std_logic_vector(7 downto 0) := x"77";

  -- binary extension mode commands - the command is indicated by bits 5:4 of the command byte
  constant binCmdNop      : std_logic_vector(1 downto 0) := "00";
  constant binCmdRead     : std_logic_vector(1 downto 0) := "01";
  constant binCmdWrite    : std_logic_vector(1 downto 0) := "10";
  
  signal   dataInHexRange : std_logic;                          -- indicates that the received data is in the range of hex number
  signal   binLastByte    : std_logic;                          -- last byte flag indicates that the current byte in the command is the last
  signal   txEndP         : std_logic;                          -- transmission end pulse
  signal   readOp         : std_logic;                          -- read operation flag
  signal   writeOp        : std_logic;                          -- write operation flag
  signal   binReadOp      : std_logic;                          -- binary mode read operation flag
  signal   binWriteOp     : std_logic;                          -- binary mode write operation flag
  signal   sendStatFlag   : std_logic;                          -- send status flag
  signal   addrAutoInc    : std_logic;                          -- address auto increment mode
  signal   dataParam      : std_logic_vector(7 downto 0);       -- operation data parameter
  signal   dataNibble     : std_logic_vector(3 downto 0);       -- data nibble from received character
  signal   addrParam      : std_logic_vector(15 downto 0);      -- operation address parameter
  signal   addrNibble     : std_logic_vector(3 downto 0);       -- data nibble from received character
  signal   binByteCount   : std_logic_vector(7 downto 0);       -- binary mode byte counter
  signal   iIntAddress    : std_logic_vector(intAddress'range); -- 
  signal   iWriteReq      : std_logic;                          -- 
  signal   iIntWrite      : std_logic;                          -- 
  signal   readDone       : std_logic;                          -- internally generated read done flag
  signal   readDoneS      : std_logic;                          -- sampled read done
  signal   readDataS      : std_logic_vector(7 downto 0);       -- sampled read data
  signal   iReadReq       : std_logic;                          -- 
  signal   iIntRead       : std_logic;                          -- 
  signal   txChar         : std_logic_vector(7 downto 0);       -- transmit byte from nibble to character conversion
  signal   sTxBusy        : std_logic;                          -- sampled tx_busy for falling edge detection
  signal   txNibble       : std_logic_vector(3 downto 0);       -- nibble value for transmission

  -- module implementation
  -- main state machine
  begin
    process (clr, clk)
    begin
      if (clr = '1') then
        mainSm <= mainIdle;
      elsif (rising_edge(clk)) then
        if (newRxData = '1') then
          case mainSm is
            -- wait for a read ('r') or write ('w') command
            -- binary extension - an all zeros byte enabled binary commands 
            when mainIdle =>
              -- check received character
              if (rxData = charNul) then
                -- an all zeros received byte enters binary mode
                mainSm <= mainBinCmd;
              elsif ((rxData = charRLow) or (rxData = charRHigh)) then
                -- on read wait to receive only address field
                mainSm <= mainWhite2;
              elsif ((rxData = charWLow) or (rxData = charWHigh)) then
                -- on write wait to receive data and address
                mainSm <= mainWhite1;
              elsif ((rxData = charCR) or (rxData = charLF)) then
                -- on new line sta in idle
                mainSm <= mainIdle;
              else
                -- any other character wait to end of line (EOL)
                mainSm <= mainEol;
              end if;
            -- wait for white spaces till first data nibble 
            when mainWhite1 =>
              -- wait in this case until any white space character is received. in any
              -- valid character for data value switch to data state. a new line or carriage
              -- return should reset the state machine to idle.
              -- any other character transitions the state machine to wait for EOL.
              if ((rxData = charSpace) or (rxData = charTab)) then
                mainSm <= mainWhite1;
              elsif (dataInHexRange = '1') then
                mainSm <= mainData;
              elsif ((rxData = charCR) or (rxData = charLF)) then
                mainSm <= mainIdle;
              else
                mainSm <= mainEol;
              end if;
            -- receive data field
            when mainData =>
              -- wait while data in hex range. white space transition to wait white 2 state.
              -- CR and LF resets the state machine. any other value cause state machine to
              -- wait til end of line.
              if (dataInHexRange = '1') then
                mainSm <= mainData;
              elsif ((rxData = charSpace) or (rxData = charTab)) then
                mainSm <= mainWhite2;
              elsif ((rxData = charCR) or (rxData = charLF)) then
                mainSm <= mainIdle;
              else
                mainSm <= mainEol;
              end if;
            -- wait for white spaces till first address nibble
            when mainWhite2 =>
              -- similar to MAIN_WHITE1
              if ((rxData = charSpace) or (rxData = charTab)) then
                mainSm <= mainWhite2;
              elsif (dataInHexRange = '1') then
                mainSm <= mainAddr;
              elsif ((rxData = charCR) or (rxData = charLF)) then
                mainSm <= mainIdle;
              else
                mainSm <= mainEol;
              end if;
            -- receive address field
            when mainAddr =>
              -- similar to MAIN_DATA
              if (dataInHexRange = '1') then
                mainSm <= mainAddr;
              elsif ((rxData = charCR) or (rxData = charLF)) then
                mainSm <= mainIdle;
              else
                mainSm <= mainEol;
              end if;
            -- wait to EOL
            when mainEol =>
              -- wait for CR or LF to move back to idle
              if ((rxData = charCR) or (rxData = charLF)) then
                mainSm <= mainIdle;
              end if;
            -- binary extension
            -- wait for command - one byte
            when mainBinCmd =>
              -- check if command is a NOP command
              if (rxData(5 downto 4) = binCmdNop) then
                -- if NOP command then switch back to idle state
                mainSm <= mainIdle;
              else
                -- not a NOP command, continue receiving parameters
                mainSm <= mainBinAdrh;
              end if;
            -- wait for address parameter - two bytes
            -- high address byte
            when mainBinAdrh =>
              -- switch to next state
              mainSm <= mainBinAdrl;
            -- low address byte
            when mainBinAdrl =>
              -- switch to next state
              mainSm <= mainBinLen;
            -- wait for length parameter - one byte
            when mainBinLen =>
              -- check if write command else command reception ended
              if (binWriteOp = '1') then
                -- wait for write data
                mainSm <= mainBinData;
              else
                -- command reception has ended
                mainSm <= mainIdle;
              end if;
            -- on write commands wait for data till end of buffer as specified by length parameter
            when mainBinData =>
              -- if this is the last data byte then return to idle
              if (binLastByte = '1') then
                mainSm <= mainIdle;
              end if;
            -- go to idle
            when others =>
              mainSm <= mainIdle;
          end case;
        end if;
      end if;
    end process;
    -- read operation flag
    -- write operation flag
    -- binary mode read operation flag
    -- binary mode write operation flag
    process (clr, clk)
    begin
      if (clr = '1') then
        readOp <= '0';
        writeOp <= '0';
        binReadOp <= '0';
        binWriteOp <= '0';
      elsif (rising_edge(clk)) then
        if ((mainSm = mainIdle) and (newRxData = '1')) then
          -- the read operation flag is set when a read command is received in idle state and cleared
          -- if any other character is received during that state.
          if ((rxData = charRLow) or (rxData = charRHigh)) then
            readOp <= '1';
          else
            readOp <= '0';
          end if;
          -- the write operation flag is set when a write command is received in idle state and cleared 
          -- if any other character is received during that state.
          if ((rxData = charWLow) or (rxData = charWHigh)) then
            writeOp <= '1';
          else
            writeOp <= '0';
          end if;
        end if;
        if ((mainSm = mainBinCmd) and (newRxData = '1') and (rxData(5 downto 4) = binCmdRead)) then
          -- read command is started on reception of a read command
          binReadOp <= '1';
        elsif ((binReadOp = '1') and (txEndP = '1') and (binLastByte = '1')) then
          -- read command ends on transmission of the last byte read
          binReadOp <= '0';
        end if;
        if ((mainSm = mainBinCmd) and (newRxData = '1') and (rxData(5 downto 4) = binCmdWrite)) then
          -- write command is started on reception of a write command
          binWriteOp <= '1';
        elsif ((mainSm = mainBinData) and (newRxData = '1') and (binLastByte = '1')) then
          binWriteOp <= '0';
        end if;
      end if;
    end process;
    -- send status flag - used only in binary extension mode
    -- address auto increment - used only in binary extension mode
    process (clr, clk)
    begin
      if (clr = '1') then
        sendStatFlag <= '0';
        addrAutoInc <= '0';
      elsif (rising_edge(clk)) then
        if ((mainSm = mainBinCmd) and (newRxData = '1')) then
          -- check if a status byte should be sent at the end of the command
          sendStatFlag <= rxData(0);
          -- check if address should be automatically incremented or not.
          -- Note that when rx_data[1] is set, address auto increment is disabled.
          addrAutoInc <= not(rxData(1));
        end if;
      end if;
    end process;
    -- operation data parameter
    process (clr, clk)
    begin
      if (clr = '1') then
        dataParam <= (others => '0');
      elsif (rising_edge(clk)) then
        if ((mainSm = mainWhite1) and (newRxData = '1') and (dataInHexRange = '1')) then
          dataParam <= "0000" & dataNibble;
        elsif ((mainSm = mainData) and (newRxData = '1') and (dataInHexRange = '1')) then
          dataParam <= dataParam(3 downto 0) & dataNibble;
        end if;
      end if;
    end process;
    -- operation address parameter
    process (clr, clk)
    begin
      if (clr = '1') then
        addrParam <= (others => '0');
      elsif (rising_edge(clk)) then
        if ((mainSm = mainWhite2) and (newRxData = '1') and (dataInHexRange = '1')) then
          addrParam <= x"000" & dataNibble;
        elsif ((mainSm = mainAddr) and (newRxData = '1') and (dataInHexRange = '1')) then
          addrParam <= addrParam(11 downto 0) & dataNibble;
        -- binary extension
        elsif (mainSm = mainBinAdrh) then
          addrParam(15 downto 8) <= rxData;
        elsif (mainSm = mainBinAdrl) then
          addrParam(7 downto 0) <= rxData;
        end if;
      end if;
    end process;
    -- binary mode command byte counter is loaded with the length parameter and counts down to zero.
    -- NOTE: a value of zero for the length parameter indicates a command of 256 bytes.
    process (clr, clk)
    begin
      if (clr = '1') then
        binByteCount <= (others => '0');
      elsif (rising_edge(clk)) then
        if ((mainSm = mainBinLen) and (newRxData = '1')) then
          binByteCount <= rxData;
        elsif (((mainSm = mainBinData) and (binWriteOp = '1') and (newRxData = '1')) or ((binReadOp = '1') and (txEndP = '1'))) then
          -- byte counter is updated on every new data received in write operations and for every 
          -- byte transmitted for read operations.
          binByteCount <= binByteCount - 1;
        end if;
      end if;
    end process;
    -- internal write control and data
    -- internal read control
    process (clr, clk)
    begin
      if (clr = '1') then
        iReadReq <= '0';
        iIntRead <= '0';
        iWriteReq <= '0';
        iIntWrite <= '0';
        intWrData <= (others => '0');
      elsif (rising_edge(clk)) then
        if ((mainSm = mainAddr) and (writeOp = '1') and (newRxData = '1') and (dataInHexRange = '0')) then
          iWriteReq <= '1';
          intWrData <= dataParam;
        -- binary extension mode
        elsif ((mainSm = mainBinData) and (binWriteOp = '1') and (newRxData = '1')) then
          iWriteReq <= '1';
          intWrData <= rxData;
        elsif ((intGnt = '1') and (iWriteReq = '1')) then
          iWriteReq <= '0';
          iIntWrite <= '1';
        else
          iIntWrite <= '0';
        end if;
        if ((mainSm = mainAddr) and (readOp = '1') and (newRxData = '1') and (dataInHexRange = '0')) then
          iReadReq <= '1';
        -- binary extension
        elsif ((mainSm = mainBinLen) and (binReadOp = '1') and (newRxData = '1')) then
          -- the first read request is issued on reception of the length byte
          iReadReq <= '1';
        elsif ((binReadOp = '1') and (txEndP = '1') and (binLastByte = '0')) then
          -- the next read requests are issued after the previous read value was transmitted and
          -- this is not the last byte to be read.
          iReadReq <= '1';
        elsif ((intGnt = '1') and (iReadReq = '1')) then
          iReadReq <= '0';
          iIntRead <= '1';
        else
          iIntRead <= '0';
        end if;
      end if;
    end process;
    -- internal address
    process (clr, clk)
    begin
      if (clr = '1') then
        iIntAddress <= (others => '0');
      elsif (rising_edge(clk)) then
        if ((mainSm = mainAddr) and (newRxData = '1') and (dataInHexRange = '0')) then
          iIntAddress <= addrParam(AW - 1 downto 0);
        -- binary extension
        elsif ((mainSm = mainBinLen) and (newRxData = '1')) then
          -- sample address parameter on reception of length byte
          iIntAddress <= addrParam(AW - 1 downto 0);
        elsif ((addrAutoInc = '1') and (((binReadOp = '1') and (txEndP = '1') and (binLastByte = '0')) or ((binWriteOp = '1') and (iIntWrite = '1')))) then
          -- address is incremented on every read or write if enabled
          iIntAddress <= iIntAddress + 1;
        end if;
      end if;
    end process;
    -- read done flag and sampled data read
    process (clr, clk)
    begin
      if (clr = '1') then
        readDone <= '0';
        readDoneS <= '0';
        readDataS <= (others => '0');
      elsif (rising_edge(clk)) then
        -- read done flag
        readDone <= iIntRead;
        -- sampled read done
        readDoneS <= readDone;
        -- sampled data read
        if (readDone = '1') then
          readDataS <= intRdData;
        end if;
      end if;
    end process;
    -- transmit state machine and control
    process (clr, clk)
    begin
      if (clr = '1') then
        txSm <= txIdle;
        txData <= (others => '0');
        newTxData <= '0';
      elsif (rising_edge(clk)) then
        case txSm is
          -- wait for read done indication
          when txIdle =>
            -- on end of every read operation check how the data read should be transmitted
            -- according to read type: ascii or binary.
            if (readDoneS = '1') then
              -- on binary mode read transmit byte value
              if (binReadOp = '1') then
                -- note that there is no need to change state
                txData <= readDataS;
                newTxData <= '1';
              else
                txSm <= txHiNib;
                txData <= txChar;
                newTxData <= '1';
              end if;
            -- check if status byte should be transmitted
            elsif (((sendStatFlag = '1') and (binReadOp = '1') and (txEndP = '1') and (binLastByte = '1')) or ((sendStatFlag = '1') and (binWriteOp = '1') and (newRxData = '1') and (binLastByte = '1')) or ((mainSm = mainBinCmd) and (newRxData = '1') and (rxData(5 downto 4) = binCmdNop))) then
              -- send status byte - currently a constant
              txData <= x"5A";
              newTxData <= '1';
            else
              newTxData <= '0';
            end if;
          when txHiNib =>
            -- wait for transmit to end
            if (txEndP = '1') then
              txSm <= txLoNib;
              txData <= txChar;
              newTxData <= '1';
            else
              newTxData <= '0';
            end if;
          -- wait for transmit to end
          when txLoNib =>
            if (txEndP = '1') then
              txSm <= txCharCR;
              txData <= charCR;
              newTxData <= '1';
            else
              newTxData <= '0';
            end if;
          -- wait for transmit to end
          when txCharCR =>
            if (txEndP = '1') then
              txSm <= txCharLF;
              txData <= charLF;
              newTxData <= '1';
            else
              newTxData <= '0';
            end if;
          -- wait for transmit to end
          when txCharLF =>
            if (txEndP = '1') then
              txSm <= txIdle;
            end if;
            -- clear tx new data flag
            newTxData <= '0';
          -- return to idle
          when others =>
            txSm <= txIdle;
        end case;
      end if;
    end process;
    -- sampled tx_busy
    process (clr, clk)
    begin
      if (clr = '1') then
        sTxBusy <= '1';
      elsif (rising_edge(clk)) then
        sTxBusy <= txBusy;
      end if;
    end process;
    -- indicates that the received data is in the range of hex number
    dataInHexRange <= '1' when (((rxData >= charZero) and (rxData <= charNine)) or
                               ((rxData >= charAHigh) and (rxData <= charFHigh)) or
                               ((rxData >= charALow) and (rxData <= charFLow))) else '0';
    -- last byte in command flag
    binLastByte <= '1' when (binByteCount = x"01") else '0';
    -- select the nibble to the nibble to character conversion
    txNibble <= readDataS(3 downto 0) when (txSm = txHiNib) else readDataS(7 downto 4);
    -- tx end pulse
    txEndP <= '1' when ((txBusy = '0') and (sTxBusy = '1')) else '0';
    -- character to nibble conversion
    with rxData select
      dataNibble <= x"0" when charZero,
                    x"1" when charOne,
                    x"2" when charTwo,
                    x"3" when charThree,
                    x"4" when charFour,
                    x"5" when charFive,
                    x"6" when charSix,
                    x"7" when charSeven,
                    x"8" when charEight,
                    x"9" when charNine,
                    x"A" when charALow,
                    x"A" when charAHigh,
                    x"B" when charBLow,
                    x"B" when charBHigh,
                    x"C" when charCLow,
                    x"C" when charCHigh,
                    x"D" when charDLow,
                    x"D" when charDHigh,
                    x"E" when charELow,
                    x"E" when charEHigh,
                    x"F" when charFLow,
                    x"F" when charFHigh,
                    x"F" when others;
    -- nibble to character conversion
    with txNibble select
      txChar <= charZero when x"0",
                charOne when x"1",
                charTwo when x"2",
                charThree when x"3",
                charFour when x"4",
                charFive when x"5",
                charSix when x"6",
                charSeven when x"7",
                charEight when x"8",
                charNine when x"9",
                charAHigh when x"A",
                charBHigh when x"B",
                charCHigh when x"C",
                charDHigh when x"D",
                charEHigh when x"E",
                charFHigh when x"F",
                charFHigh when others;
    intAddress <= iIntAddress;
    intWrite <= iIntWrite;
    intRead <= iIntRead;
    intReq <= '1' when (iReadReq = '1') else
              '1' when (iWriteReq = '1') else '0';
  end Behavioral;
