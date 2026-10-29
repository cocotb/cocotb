configuration config_single of testbench is
    for myconfig
        for dut_inst : dut
                use entity work.dut(single);
        end for;
    end for;
end configuration config_single;

configuration config_double of testbench is
    for myconfig
        for dut_inst : dut
                use entity work.dut(double);
        end for;
    end for;
end configuration config_double;
