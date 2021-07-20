-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause
library blib;

entity a is
  port ( x : in boolean );
end;

architecture structural of a is
begin
  b : entity blib.b port map (x);
end;
