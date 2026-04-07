-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library work;
use work.integers_pkg.all;

entity top is
port (
    integer_input: in integer;
    natural_input: in natural;
    positive_input: in positive;
    my_integer_input: in my_integer
);
end entity top;

architecture rtl of top is
    signal integer_signal: integer;
    signal natural_signal: natural;
    signal positive_signal: positive;
    signal my_integer_signal: my_integer;
begin
end architecture rtl;
