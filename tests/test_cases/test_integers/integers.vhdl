-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

entity top is
port (
    integer_input: in integer;
    natural_input: in natural;
    positive_input: in positive
);
end entity top;

architecture rtl of top is
    signal integer_signal: integer;
    signal natural_signal: natural;
    signal positive_signal: positive;
begin
    integer_signal <= integer_input;
    natural_signal <= natural_input;
    positive_signal <= positive_input;
end architecture rtl;
