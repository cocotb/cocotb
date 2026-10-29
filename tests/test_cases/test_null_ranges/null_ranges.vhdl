-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library ieee;
use ieee.std_logic_1164.all;

use work.null_ranges_pkg.unsignedArrayType;

entity null_ranges_top is
  port(
    null_vector_port_to     : in std_logic_vector(10 to 4);
    null_vector_port_downto : in std_logic_vector(-1 downto 0);
    null_array_port_to      : in unsignedArrayType(0 to -1);
    null_array_port_downto  : in unsignedArrayType(-7 downto 0);
    null_string_port_to     : in string(3 to -2);
    null_string_port_downto : in string(0 downto 7)
  );
end entity null_ranges_top;

architecture rtl of null_ranges_top is
  signal null_vector_signal_to     : std_logic_vector(10 to 4);
  signal null_vector_signal_downto : std_logic_vector(-1 downto 0);
  signal null_array_signal_to      : unsignedArrayType(0 to -1);
  signal null_array_signal_downto  : unsignedArrayType(-7 downto 0);
  signal null_string_signal_to     : string(3 to -2);
  signal null_string_signal_downto : string(0 downto 7);
begin
end architecture rtl;
