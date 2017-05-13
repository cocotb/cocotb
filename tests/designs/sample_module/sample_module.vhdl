-------------------------------------------------------------------------------
-- Copyright (c) 2014 Potential Ventures Ltd
-- All rights reserved.
--
-- Redistribution and use in source and binary forms, with or without
-- modification, are permitted provided that the following conditions are met:
--     * Redistributions of source code must retain the above copyright
--       notice, this list of conditions and the following disclaimer.
--     * Redistributions in binary form must reproduce the above copyright
--       notice, this list of conditions and the following disclaimer in the
--       documentation and/or other materials provided with the distribution.
--     * Neither the name of Potential Ventures Ltd,
--       Copyright (c) 2013 SolarFlare Communications Inc nor the
--       names of its contributors may be used to endorse or promote products
--       derived from this software without specific prior written permission.
--
-- THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
-- ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
-- WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
-- DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
-- DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
-- (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
-- LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
-- ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
-- (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
-- SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
-------------------------------------------------------------------------------




library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.sample_module_pack.all;

entity sample_module is
    port (
        clk                             : in    std_ulogic;

        stream_in_data                  : in    std_ulogic_vector(7 downto 0);
        stream_in_data_wide             : in    std_ulogic_vector(63 downto 0);
        stream_in_valid                 : in    std_ulogic;
        stream_in_func_en               : in    std_ulogic;
        stream_in_ready                 : out   std_ulogic;
        stream_in_real                  : in    real;
        stream_in_int                   : in    integer;
        stream_in_string                : in    string(1 to 8);
        stream_in_bool                  : in    boolean;

        inout_if                        : in    test_if;

        stream_out_data_comb            : out   std_ulogic_vector(7 downto 0);
        stream_out_data_registered      : out   std_ulogic_vector(7 downto 0);
        stream_out_data_wide            : out   std_ulogic_vector(63 downto 0);
        stream_out_valid                : out   std_ulogic;
        stream_out_ready                : in    std_ulogic;
        stream_out_real                 : out   real;
        stream_out_int                  : out   integer;
        stream_out_string               : out   string(1 to 8);
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

function afunc(value : std_ulogic_vector) return std_ulogic_vector is
    variable i: integer;
    variable rv: std_ulogic_vector(7 downto 0);
begin
    i := 0;
    while i <= 7 loop
        rv(i) := value(7-i);
        i := i + 1;
    end loop;
    return rv;
end afunc;

  signal cosLut0, sinLut0 : lutType;
  signal cosLut1, sinLut1 : lutType;
  signal cosLut,  sinLut  : lutType;

begin

process (clk) begin
    if rising_edge(clk) then
        stream_out_valid           <= stream_in_valid;
        stream_out_data_registered <= stream_in_data;
    end if;
end process;

stream_out_data_comb <= afunc(stream_in_data) when stream_in_func_en = '0' else stream_in_data;
stream_in_ready      <= stream_out_ready;
stream_out_real      <= stream_in_real;
stream_out_int       <= stream_in_int;
stream_out_string    <= stream_in_string;
stream_out_bool      <= stream_in_bool;
stream_out_data_wide(3 downto 2) <= stream_in_data_wide(3 downto 2);

isample_module1 : component sample_module_1
      generic map (
        EXAMPLE_STRING  => "TESTING",
        EXAMPLE_BOOL => true,
      	EXAMPLE_WIDTH	=> 7
        )
  port map (
  clk => clk,
  stream_in_data => stream_in_data,
  stream_out_data_registered => open,
  stream_out_data_valid => open
  );

   
end architecture;
