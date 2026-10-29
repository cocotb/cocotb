-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause
library dlib;

entity c is
  port ( x : in boolean );
end;

architecture structural of c is
begin
  d : entity dlib.d port map (x);
end;
