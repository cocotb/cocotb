-- We simply connect two UARTs together in different languages
--
-- Also define a record to help the testcase


library ieee;
use ieee.std_logic_1164.all;

entity vhdl_toplevel is
  port (
    clk   : in std_ulogic;
    reset : in std_ulogic);
end;

architecture impl of vhdl_toplevel is

  type bus_struct_t is record
    address : std_logic_vector(15 downto 0);
    wr_data : std_logic_vector(7 downto 0);
    read    : std_ulogic;
    write   : std_ulogic;
  end record bus_struct_t;

  signal bus_verilog : bus_struct_t;
  signal bus_vhdl    : bus_struct_t;

  signal serial_v2h      : std_ulogic;
  signal serial_h2v      : std_ulogic;
  signal verilog_rd_data : std_logic_vector(7 downto 0);
  signal vhdl_rd_data    : std_logic_vector(7 downto 0);

begin

  i_verilog : entity work.uart2bus_top
    port map (
      -- global signals
      clock       => clk,
      reset       => reset,
      -- uart serial signals
      ser_in      => serial_h2v,
      ser_out     => serial_v2h,
      -- internal bus to register file
      int_address => bus_verilog.address,
      int_wr_data => bus_verilog.wr_data,
      int_write   => bus_verilog.write,
      int_read    => bus_verilog.read,
      int_rd_data => verilog_rd_data,

      int_req => open,
      int_gnt => '1'
      );

  i_vhdl : entity work.uart2BusTop
    generic map (
      AW => 16)                         -- [integer]
    port map (
      -- global signals
      clk        => clk,                -- [in  STD_LOGIC]
      clr        => reset,              -- [in  STD_LOGIC]
      -- uart serial signals
      serIn      => serial_v2h,         -- [in  STD_LOGIC]
      serOut     => serial_h2v,         -- [out STD_LOGIC]
      -- internal bus to register file
      intAddress => bus_vhdl.address,   -- [out STD_LOGIC_VECTOR (AW - 1 downto 0)]
      intWrData  => bus_vhdl.wr_data,   -- [out STD_LOGIC_VECTOR (7 downto 0)]
      intWrite   => bus_vhdl.write,     -- [out STD_LOGIC]
      intRead    => bus_vhdl.read,      -- [out STD_LOGIC]
      intRdData  => vhdl_rd_data,       -- [in  STD_LOGIC_VECTOR (7 downto 0)]

      intAccessReq => open,             -- [out std_logic]
      intAccessGnt => '1'               -- [in  std_logic]
      );

end architecture;
