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
--     * Neither the name of Potential Ventures Ltd nor
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
--
--
-- Endian swapping module.
--
-- Simple example with Avalon streaming interfaces and a CSR bus
--
-- Avalon-ST has readyLatency of 0
-- Avalon-MM has fixed readLatency of 1
--
-- Exposes 2 32-bit registers via the Avalon-MM interface
--
--    Address 0:  bit     0  [R/W] byteswap enable
--                bits 31-1: [N/A] reserved
--    Adress  1:  bits 31-0: [RO]  packet count
--
library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity endian_swapper_vhdl is
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

architecture impl of endian_swapper_vhdl is


function byteswap(data : in std_ulogic_vector(63 downto 0)) return std_ulogic_vector is begin
    return  data(7  downto  0) &
            data(15 downto  8) &
            data(23 downto 16) &
            data(31 downto 24) &
            data(39 downto 32) &
            data(47 downto 40) &
            data(55 downto 48) &
            data(63 downto 56);
end;

signal csr_waitrequest_int      : std_ulogic;
signal stream_out_endofpacket_int: std_ulogic;
signal flush_pipe       :       std_ulogic;
signal in_packet        :       std_ulogic;
signal byteswapping     :       std_ulogic;
signal packet_count     :       unsigned(31 downto 0);

begin


process (clk, reset_n) begin
    if (reset_n = '0') then
        flush_pipe      <= '0';
        in_packet       <= '0';
        packet_count    <= to_unsigned(0, 32);
    elsif rising_edge(clk) then


        if (flush_pipe = '1' and stream_out_ready = '1') then

            flush_pipe <= stream_in_endofpacket and stream_in_valid and stream_out_ready;

        elsif (flush_pipe = '0') then
            flush_pipe <= stream_in_endofpacket and stream_in_valid and stream_out_ready;
        end if;

        if (stream_out_ready = '1' and stream_in_valid = '1') then
            stream_out_empty            <= stream_in_empty;
            stream_out_startofpacket    <= stream_in_startofpacket;
            stream_out_endofpacket_int  <= stream_in_endofpacket;

            if (byteswapping = '0') then
                stream_out_data      <= stream_in_data;
            else
                stream_out_data      <= byteswap(stream_in_data);
            end if;

            if (stream_in_startofpacket = '1' and stream_in_valid = '1') then
                packet_count <= packet_count + 1;
                in_packet    <= '1';
            end if;

            if (stream_in_endofpacket = '1' and stream_in_valid = '1') then
                in_packet    <= '0';
            end if;
        end if;
    end if;
end process;


stream_in_ready         <= stream_out_ready;
stream_out_endofpacket  <= stream_out_endofpacket_int;

stream_out_valid        <= '1' when (stream_in_valid = '1' and stream_out_endofpacket_int = '0') or flush_pipe = '1' else '0';

-- Hold off CSR accesses during packet transfers to prevent changing of endian configuration mid-packet
csr_waitrequest_int     <= '1' when reset_n = '0' or in_packet = '1' or (stream_in_startofpacket = '1' and stream_in_valid = '1') or flush_pipe = '1' else '0';
csr_waitrequest         <= csr_waitrequest_int;

process (clk, reset_n) begin
    if (reset_n = '0') then
        byteswapping      <= '0';
        csr_readdatavalid <= '0';
    elsif rising_edge(clk) then

        if (csr_read = '1') then
            csr_readdatavalid <= not csr_waitrequest_int;

            case csr_address is
                when "00"       => csr_readdata <= (31 downto 1 => '0') & byteswapping;
                when "01"       => csr_readdata <= std_ulogic_vector(packet_count);
                when others     => csr_readdata <= (31 downto 0 => 'X');
            end case;

        elsif (csr_write = '1' and csr_waitrequest_int = '0') then
            case csr_address is
                when "00"       => byteswapping <= csr_writedata(0);
                when others     => null;
            end case;
        end if;
    end if;
end process;


-- Unfortunately this workaround is required for Aldec: Need to schedule an event
fake_process :process
begin
    wait for 50 ns;
end process;


end architecture;
