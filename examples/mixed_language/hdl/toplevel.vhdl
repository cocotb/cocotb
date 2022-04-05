-- Example using mixed-language simulation
--
-- Here we have a VHDL toplevel that instantiates both SV and VHDL
-- sub entities
library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity endian_swapper_mixed is
    generic (
        DATA_BYTES              : integer := 8);
    port (
        clk                     : in    std_ulogic;
        reset_n                 : in    std_ulogic;

        stream_in_data          : in    std_ulogic_vector(DATA_BYTES*8-1 downto 0);
        stream_in_empty         : in    std_ulogic_vector(2 downto 0);
        stream_in_valid         : in    std_ulogic;
        stream_in_startofpacket : in    std_ulogic;
        stream_in_endofpacket   : in    std_ulogic;
        stream_in_ready         : out   std_ulogic;

        stream_out_data         : out   std_ulogic_vector(DATA_BYTES*8-1 downto 0);
        stream_out_empty        : out   std_ulogic_vector(2 downto 0);
        stream_out_valid        : out   std_ulogic;
        stream_out_startofpacket: out   std_ulogic;
        stream_out_endofpacket  : out   std_ulogic;
        stream_out_ready        : in    std_ulogic;

        csr_address             : in    std_ulogic_vector(1 downto 0);
        csr_readdata            : out   std_ulogic_vector(31 downto 0);
        csr_readdatavalid       : out   std_ulogic;
        csr_read                : in    std_ulogic;
        csr_write               : in    std_ulogic;
        csr_waitrequest         : out   std_ulogic;
        csr_writedata           : in    std_ulogic_vector(31 downto 0)
    );
end;

architecture impl of endian_swapper_mixed is

    -- The SV entity is instantiated as a component because cocotb is
    -- executing vcom before vlog. Hence the toplevel VHDL file is compiled
    -- before the SV module. Therefore, an entity instantiation is not possible here.
    component endian_swapper_sv
        generic (
            DATA_BYTES              : integer := 8);
        port (
            clk                     : in    std_ulogic;
            reset_n                 : in    std_ulogic;

            stream_in_data          : in    std_ulogic_vector(DATA_BYTES*8-1 downto 0);
            stream_in_empty         : in    std_ulogic_vector(2 downto 0);
            stream_in_valid         : in    std_ulogic;
            stream_in_startofpacket : in    std_ulogic;
            stream_in_endofpacket   : in    std_ulogic;
            stream_in_ready         : out   std_ulogic;

            stream_out_data         : out   std_ulogic_vector(DATA_BYTES*8-1 downto 0);
            stream_out_empty        : out   std_ulogic_vector(2 downto 0);
            stream_out_valid        : out   std_ulogic;
            stream_out_startofpacket: out   std_ulogic;
            stream_out_endofpacket  : out   std_ulogic;
            stream_out_ready        : in    std_ulogic;

            csr_address             : in    std_ulogic_vector(1 downto 0);
            csr_readdata            : out   std_ulogic_vector(31 downto 0);
            csr_readdatavalid       : out   std_ulogic;
            csr_read                : in    std_ulogic;
            csr_write               : in    std_ulogic;
            csr_waitrequest         : out   std_ulogic;
            csr_writedata           : in    std_ulogic_vector(31 downto 0)
        );
  end component;


    signal sv_to_vhdl_data:             std_ulogic_vector(DATA_BYTES*8-1 downto 0) ;
    signal sv_to_vhdl_empty:            std_ulogic_vector(2 downto 0);
    signal sv_to_vhdl_valid:            std_ulogic;
    signal sv_to_vhdl_startofpacket:    std_ulogic;
    signal sv_to_vhdl_endofpacket:      std_ulogic;
    signal sv_to_vhdl_ready:            std_ulogic;

    signal csr_waitrequest_vhdl, csr_waitrequest_sv : std_ulogic;

begin
i_swapper_sv : endian_swapper_sv
    generic map (
        DATA_BYTES              =>      DATA_BYTES
    ) port map (
        clk                     =>      clk,
        reset_n                 =>      reset_n,

        stream_in_empty         =>      stream_in_empty,
        stream_in_data          =>      stream_in_data,
        stream_in_endofpacket   =>      stream_in_endofpacket,
        stream_in_startofpacket =>      stream_in_startofpacket,
        stream_in_valid         =>      stream_in_valid,
        stream_in_ready         =>      stream_in_ready,

        stream_out_empty        =>      sv_to_vhdl_empty,
        stream_out_data         =>      sv_to_vhdl_data,
        stream_out_endofpacket  =>      sv_to_vhdl_endofpacket,
        stream_out_startofpacket=>      sv_to_vhdl_startofpacket,
        stream_out_valid        =>      sv_to_vhdl_valid,
        stream_out_ready        =>      sv_to_vhdl_ready,

        csr_address             =>      csr_address,
        csr_readdata            =>      csr_readdata,
        csr_readdatavalid       =>      csr_readdatavalid,
        csr_read                =>      csr_read,
        csr_write               =>      csr_write,
        csr_waitrequest         =>      csr_waitrequest_sv,
        csr_writedata           =>      csr_writedata
    );



i_swapper_vhdl : entity work.endian_swapper_vhdl
generic map (
    DATA_BYTES              =>      DATA_BYTES
) port map (
    clk                     =>      clk,
    reset_n                 =>      reset_n,

    stream_in_empty         =>      sv_to_vhdl_empty,
    stream_in_data          =>      sv_to_vhdl_data,
    stream_in_endofpacket   =>      sv_to_vhdl_endofpacket,
    stream_in_startofpacket =>      sv_to_vhdl_startofpacket,
    stream_in_valid         =>      sv_to_vhdl_valid,
    stream_in_ready         =>      sv_to_vhdl_ready,

    stream_out_empty        =>      stream_out_empty,
    stream_out_data         =>      stream_out_data,
    stream_out_endofpacket  =>      stream_out_endofpacket,
    stream_out_startofpacket=>      stream_out_startofpacket,
    stream_out_valid        =>      stream_out_valid,
    stream_out_ready        =>      stream_out_ready,

    csr_address             =>      csr_address,
    csr_readdata            =>      open,
    csr_readdatavalid       =>      open,
    csr_read                =>      csr_read,
    csr_write               =>      csr_write,
    csr_waitrequest         =>      csr_waitrequest_vhdl,
    csr_writedata           =>      csr_writedata
);


    csr_waitrequest <= csr_waitrequest_sv or csr_waitrequest_vhdl;
end architecture;
