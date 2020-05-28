library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity sample_module_1 is
    generic (
        EXAMPLE_STRING      : string;
        EXAMPLE_BOOL        : boolean;
        EXAMPLE_WIDTH       : integer
    );
    port (
        clk                             : in     std_ulogic;
        stream_in_data                  : in     std_ulogic_vector(EXAMPLE_WIDTH downto 0);
        stream_out_data_registered      : buffer std_ulogic_vector(EXAMPLE_WIDTH downto 0);
        stream_out_data_valid           : out    std_ulogic
    );
end;

architecture impl of sample_module_1 is
begin
    process (clk) begin
        if rising_edge(clk) then
            stream_out_data_registered <= stream_in_data;
        end if;
    end process;

    stream_out_data_valid  <= '1' when (stream_out_data_registered(EXAMPLE_WIDTH) = '1') else '0';

    SAMPLE_BLOCK : block
        signal clk_inv : std_ulogic;
    begin
        clk_inv <= not clk;
    end block;

end architecture;
