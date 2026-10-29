-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause
library elib;

entity d is
  port ( x : in boolean );
end;

architecture structural of d is
begin
  e : entity elib.e port map (x);
end;
