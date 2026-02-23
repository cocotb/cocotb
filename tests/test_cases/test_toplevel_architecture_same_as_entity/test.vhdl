-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

entity test is
    port ( x : in boolean );
end entity test;

architecture test of test is
begin
    -- This architecture has the same name as the entity, which is
    -- what this testcase is testing.
end architecture test;
