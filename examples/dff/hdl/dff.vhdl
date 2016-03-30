-- Copyright (c) 2016 Technische Universitaet Dresden, Germany
-- Chair for VLSI-Design, Diagnostic and Architecture
-- Author: Martin Zabel
-- All rights reserved.
--
-- A simple D flip-flop

library ieee;
use ieee.std_logic_1164.all;

entity dff is
  port (
    c : in  std_logic;
    d : in  std_logic;
    q : out std_logic := '0');
end entity dff;

architecture rtl of dff is
begin
  q <= d when rising_edge(c);
end architecture rtl;
