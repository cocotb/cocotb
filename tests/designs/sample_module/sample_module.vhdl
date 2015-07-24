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

entity sample_module is
    port (
        clk                             : in    std_ulogic;

        stream_in_data                  : in    std_ulogic_vector(7 downto 0);
        stream_in_data_wide             : in    std_ulogic_vector(63 downto 0);
        stream_in_valid                 : in    std_ulogic;
        stream_in_ready                 : out   std_ulogic;

        stream_out_data_comb            : out   std_ulogic_vector(7 downto 0);
        stream_out_data_registered      : out   std_ulogic_vector(7 downto 0);
        stream_out_ready                : in    std_ulogic
    );
end;

architecture impl of sample_module is

begin

process (clk) begin
    if rising_edge(clk) then
        stream_out_data_registered <= stream_in_data;
    end if;
end process;

stream_out_data_comb <= stream_in_data;
stream_in_ready      <= stream_out_ready;

end architecture;