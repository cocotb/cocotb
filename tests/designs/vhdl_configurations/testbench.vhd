library ieee;
use ieee.std_logic_1164.all;

entity testbench is
end entity testbench;

architecture myconfig of testbench is
    component dut
        port(
            clk      : in  std_ulogic;
            data_in  : in  std_ulogic;
            data_out : out std_ulogic);
    end component dut;

    signal clk          : std_ulogic;
    signal data_in      : std_ulogic;
    signal data_out     : std_ulogic;

begin

    dut_inst : component dut
        port map(
            clk         => clk,
            data_in     => data_in,
            data_out    => data_out
        );
end architecture myconfig;
