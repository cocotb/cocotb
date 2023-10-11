-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

entity test is
    port ( o : out bit_vector(15 downto 0) );
end entity test;

architecture rtl of test is
begin

    foobar: for i in 0 to 9 generate
    begin
        o(i) <= '1';
    end generate;

    -- Should not be confused with "foobar" which shares the same prefix
    foo: for i in 10 to 15 generate
    begin
        o(i) <= '1';
    end generate;

end architecture rtl;
