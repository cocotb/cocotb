-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause
library clib;

entity b is
  port ( x : in boolean );
end;

architecture structural of b is
begin
  c : entity clib.c port map (x);
end;
