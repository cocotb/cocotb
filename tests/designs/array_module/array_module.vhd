-- Copyright cocotb contributors
-- Copyright (c) 2016 Potential Ventures Ltd
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.array_module_pack.all;

entity array_module is
    generic (
        param_logic                    :       std_logic                     := '1';
        param_logic_vec                :       std_logic_vector(7 downto 0)  := X"DA";
        param_bool                     :       boolean                       := TRUE;
        param_int                      :       integer                       := 6;
        param_real                     :       real                          := 3.14;
        param_char                     :       character                     := 'p';
        param_str                      :       string(1 to 8)                := "ARRAYMOD";
        param_rec                      :       rec_type                      := REC_TYPE_ZERO;
        param_cmplx                    :       rec_array(0 to 1)             := (others=>REC_TYPE_ZERO)
    );
    port (
        clk                            : in    std_logic;

        select_in                      : in    integer;

        port_desc_in                   : in    std_logic_vector(7 downto 0);
        port_asc_in                    : in    std_logic_vector(0 to 7);
        port_ofst_in                   : in    std_logic_vector(1 to 8);

        port_desc_out                  :   out std_logic_vector(7 downto 0);
        port_asc_out                   :   out std_logic_vector(0 to 7);
        port_ofst_out                  :   out std_logic_vector(1 to 8);

        port_logic_out                 :   out std_logic;
        port_logic_vec_out             :   out std_logic_vector(7 downto 0);
        port_bool_out                  :   out boolean;
        port_int_out                   :   out integer;
        port_real_out                  :   out real;
        port_char_out                  :   out character;
        port_str_out                   :   out string(1 to 8);
        port_rec_out                   :   out rec_type;
        port_cmplx_out                 :   out rec_array(0 to 1)
    );
end;

architecture impl of array_module is
    constant const_logic               : std_logic                     := '0';
    constant const_logic_vec           : std_logic_vector(7 downto 0)  := X"3D";
    constant const_bool                : boolean                       := FALSE;
    constant const_int                 : integer                       := 12;
    constant const_real                : real                          := 6.28;
    constant const_char                : character                     := 'c';
    constant const_str                 : string(1 to 8)                := "MODARRAY";
    constant const_rec                 : rec_type                      := REC_TYPE_ONE;
    constant const_cmplx               : rec_array(1 to 2)             := (others=>REC_TYPE_ONE);

    signal   sig_desc      : std_logic_vector(23 downto 16);
    signal   sig_asc       : std_logic_vector(16 to 23);

    signal   \ext_id\      : std_logic;
    signal   \!\           : std_logic;

    signal   sig_t1        : t1;
    signal   sig_t2        : t2;
    signal   sig_t3a       : t3(1 to 4);
    signal   sig_t3b       : t3(3 downto 0);
    signal   sig_t4        : t4;
    signal   sig_t5        : t5;
    signal   sig_t6        : t6(0 to 1, 2 to 4);

    signal   sig_logic     : std_logic;
    signal   sig_logic_vec : std_logic_vector(7 downto 0);
    signal   sig_bool      : boolean;
    signal   sig_int       : integer;
    signal   sig_real      : real;
    signal   sig_char      : character;
    signal   sig_str       : string(1 to 8);
    signal   sig_rec       : rec_type;
    signal   sig_cmplx     : rec_array(0 to 1);
begin
    port_ofst_out <= port_ofst_in;

    sig_proc : process (clk)
    begin
        if (rising_edge(clk)) then
            if (select_in = 1) then
                port_logic_out     <= const_logic;
                port_logic_vec_out <= const_logic_vec;
                port_bool_out      <= const_bool;
                port_int_out       <= const_int;
                port_real_out      <= const_real;
                port_char_out      <= const_char;
                port_str_out       <= const_str;
                port_rec_out       <= const_rec;
                port_cmplx_out     <= const_cmplx;
            elsif (select_in = 2) then
                port_logic_out     <= sig_logic;
                port_logic_vec_out <= sig_logic_vec;
                port_bool_out      <= sig_bool;
                port_int_out       <= sig_int;
                port_real_out      <= sig_real;
                port_char_out      <= sig_char;
                port_str_out       <= sig_str;
                port_rec_out       <= sig_rec;
                port_cmplx_out     <= sig_cmplx;
            else
                port_logic_out     <= param_logic;
                port_logic_vec_out <= param_logic_vec;
                port_bool_out      <= param_bool;
                port_int_out       <= param_int;
                port_real_out      <= param_real;
                port_char_out      <= param_char;
                port_str_out       <= param_str;
                port_rec_out       <= param_rec;
                port_cmplx_out     <= param_cmplx;
            end if;
        end if;
    end process sig_proc;

    asc_gen : for idx1 in sig_asc'range generate
        constant OFFSET : natural   := sig_asc'left - port_asc_in'left;
        signal   sig    : std_logic;
    begin
        sig                       <= port_asc_in(idx1-OFFSET) when rising_edge(clk);
        sig_asc(idx1)             <= sig;
        port_asc_out(idx1-OFFSET) <= sig_asc(idx1);
    end generate asc_gen;

    desc_gen : for idx2 in port_desc_in'range generate
        constant OFFSET : natural := sig_desc'left - port_desc_in'left;
        signal   sig    : std_logic;
    begin
        sig                   <= port_desc_in(idx2) when rising_edge(clk);
        sig_desc(idx2+OFFSET) <= sig;
        port_desc_out(idx2)   <= sig_desc(idx2+OFFSET);
    end generate desc_gen;
end architecture;
