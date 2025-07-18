-- Copyright cocotb contributors
-- Copyright (c) 2014 Potential Ventures Ltd
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause




library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.sample_module_package.all;

entity sample_module is
    generic (
        INT_PARAM                       : integer   := 123
    );
    port (
        clk                             : in    std_ulogic;

        stream_in_data                  : in    std_ulogic_vector(7 downto 0);
        stream_in_data_dword            : in    std_ulogic_vector(31 downto 0);
        stream_in_data_39bit            : in    std_ulogic_vector(38 downto 0);
        stream_in_data_wide             : in    std_ulogic_vector(63 downto 0);
        stream_in_data_dqword           : in    std_ulogic_vector(127 downto 0);
        stream_in_valid                 : in    std_ulogic;
        stream_in_ready                 : out   std_ulogic;
        stream_in_real                  : in    real;
        stream_in_int                   : in    integer;
        stream_in_string                : in    string(1 to 64);
        stream_in_bool                  : in    boolean;

        inout_if                        : in    test_record;

        stream_out_data_comb            : out   std_ulogic_vector(7 downto 0);
        stream_out_data_registered      : out   std_ulogic_vector(7 downto 0);
        stream_out_data_wide            : out   std_ulogic_vector(63 downto 0);
        stream_out_ready                : in    std_ulogic;
        stream_out_real                 : out   real;
        stream_out_int                  : out   integer;
        stream_out_string               : out   string(1 to 64);
        stream_out_bool                 : out   boolean
    );
end;

architecture impl of sample_module is

    component sample_module_1 is
        generic (
            EXAMPLE_STRING      : string;
            EXAMPLE_BOOL        : boolean;
            EXAMPLE_WIDTH       : integer
        );
        port (
            clk                             : in    std_ulogic;
            stream_in_data                  : in    std_ulogic_vector(EXAMPLE_WIDTH downto 0);
            stream_out_data_registered      : buffer   std_ulogic_vector(EXAMPLE_WIDTH downto 0);
            stream_out_data_valid           : out   std_ulogic
        );
    end component sample_module_1;

    type lutType is array (0 to 3, 0 to 6) of signed(10 downto 0);

    signal cosLut0, sinLut0 : lutType;
    signal cosLut1, sinLut1 : lutType;
    signal cosLut,  sinLut  : lutType;

    type unsignedArrayType is array (natural range <>) of unsigned(7 downto 0);
    signal array_7_downto_4 : unsignedArrayType(7 downto 4);
    signal array_4_to_7     : unsignedArrayType(4 to 7);
    signal array_4_downto_7 : unsignedArrayType(4 downto 7);
    signal array_3_downto_0 : unsignedArrayType(3 downto 0);
    signal array_0_to_3     : unsignedArrayType(0 to 3);

    type twoDimArrayType is array (natural range <>) of unsignedArrayType(31 downto 28);
    signal array_2d         : twoDimArrayType(0 to 1);

    constant NUM_OF_MODULES : natural := 4;
    signal temp             : std_logic_vector(NUM_OF_MODULES-1 downto 0);

    signal stream_in_string_asciival_sum : natural;

    -- for testing weird signal names
    signal \weird.signal(1)\              : std_ulogic_vector(3 downto 0);
    signal \weird.signal(2)\              : std_ulogic_vector(3 downto 0);
    signal \(.*|this looks like a regex)\ : std_ulogic_vector(3 downto 0);

    -- for testing HierarchyArrayObject typing
    constant NUM_TEST_MODULES : natural := 4;

begin

    -- Generate array of test modules for HierarchyArrayObject typing test
    arr: for i in 0 to NUM_TEST_MODULES-1 generate
    begin
        test_mod : component sample_module_1
            generic map (
                EXAMPLE_STRING => "TEST" & integer'image(i),
                EXAMPLE_BOOL => true,
                EXAMPLE_WIDTH => 7
            )
            port map (
                clk => clk,
                stream_in_data => stream_in_data,
                stream_out_data_registered => open,
                stream_out_data_valid => open
            );
    end generate arr;

    genblk1: for i in NUM_OF_MODULES - 1 downto 0 generate
    begin
        process (clk) begin
            if rising_edge(clk) then
                temp(i) <= '0';
            end if;
        end process;
    end generate;

    process (clk) begin
        if rising_edge(clk) then
            stream_out_data_registered <= stream_in_data;
        end if;
    end process;

    process (stream_in_string) is
      variable v_cur_char : character;
      variable v_stream_in_string_asciival : natural;
      variable v_stream_in_string_asciival_sum : natural;
    begin
      report "stream_in_string has been updated, new value is '" & stream_in_string & "'";
      v_stream_in_string_asciival_sum := 0;
      for v_idx in stream_in_string'range loop
        v_cur_char := stream_in_string(v_idx);
        if v_cur_char /= ' ' then  -- only work on non-space characters
          v_stream_in_string_asciival := character'pos(v_cur_char);
          v_stream_in_string_asciival_sum := v_stream_in_string_asciival_sum + v_stream_in_string_asciival;
          -- report "v_idx=" & integer'image(v_idx) &
          --   ", v_stream_in_string_asciival=" & integer'image(v_stream_in_string_asciival) &
          --   -- ", v_cur_char='" & v_cur_char & "'" &  -- this often ends the report output here
          --   " -> v_stream_in_string_asciival_sum=" & integer'image(v_stream_in_string_asciival_sum);
        end if;
      end loop;  -- v_idx
      stream_in_string_asciival_sum <= v_stream_in_string_asciival_sum;
    end process;

    process (stream_in_data) is
    begin
        stream_out_data_comb <= stream_in_data;
    end process;

    stream_in_ready      <= stream_out_ready;
    stream_out_real      <= stream_in_real;
    stream_out_int       <= stream_in_int;
    stream_out_string    <= stream_in_string;
    stream_out_bool      <= stream_in_bool;
    stream_out_data_wide(3 downto 2) <= stream_in_data_wide(3 downto 2);

    isample_module1 : component sample_module_1
        generic map (
            EXAMPLE_STRING => "TESTING",
            EXAMPLE_BOOL => true,
            EXAMPLE_WIDTH => 7
        )
        port map (
            clk => clk,
            stream_in_data => stream_in_data,
            stream_out_data_registered => open,
            stream_out_data_valid => open
        );

end architecture;
