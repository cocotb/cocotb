-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause
entity e is
  port ( x : in boolean );
end;


architecture structural of e is
begin
  process(x) begin
    report e'instance_name;
  end process;
end;
