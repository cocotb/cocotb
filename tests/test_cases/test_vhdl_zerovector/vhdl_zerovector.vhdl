-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library ieee;
use ieee.std_logic_1164.all;

entity vhdl_zerovector is
  generic(DataWidth  : natural := 8;
          CntrlWidth : natural := 0);
  port(Data_in   : in  std_logic_vector(DataWidth - 1 downto 0);
       Data_out  : out std_logic_vector(DataWidth - 1 downto 0);
       Cntrl_in  : in  std_logic_vector(CntrlWidth - 1 downto 0);
       Cntrl_out : out std_logic_vector(CntrlWidth - 1 downto 0));
end entity vhdl_zerovector;

architecture RTL of vhdl_zerovector is
begin
  Data_out  <= Data_in;
  Cntrl_out <= Cntrl_in;
end architecture RTL;
