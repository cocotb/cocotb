library ieee;
use ieee.std_logic_1164.all;

entity dut is
    port(
        clk      : in  std_ulogic;
        data_in  : in  std_ulogic;
        data_out : out std_ulogic
    );
end entity dut;

architecture single of dut is begin

    report_p : process begin
        report "this is dut(single)";
        wait;
    end process;

    clocked_p : process(clk) is begin
        if rising_edge(clk) then
            data_out <=  data_in;
        end if;
    end process;
end architecture single;


architecture double of dut is
    signal data_in_r  : std_ulogic;
begin

    report_p : process begin
        report "this is dut(double)";
        wait;
    end process;

    clocked_p : process(clk) is begin
        if rising_edge(clk) then
            data_in_r <=  data_in;
            data_out  <=  data_in_r;
        end if;
    end process;
end architecture double;
