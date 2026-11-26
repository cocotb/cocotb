-- This file is public domain, it can be freely copied without restrictions.
-- SPDX-License-Identifier: CC0-1.0

library ieee;
use ieee.std_logic_1164.all;

-- Drives an 8-bit bus while `drive_en` is high and leaves it floating otherwise, so the bus can be
-- used by someone else in between.
entity bus_master is
  port (
    data_bus : inout std_logic_vector(7 downto 0);
    drive_en : in    std_logic;
    data_out : in    std_logic_vector(7 downto 0);
    data_in  : out   std_logic_vector(7 downto 0)
  );
end entity;

architecture a of bus_master is
begin
  data_bus <= data_out when drive_en = '1' else (others => 'Z');
  data_in  <= data_bus;
end architecture;
