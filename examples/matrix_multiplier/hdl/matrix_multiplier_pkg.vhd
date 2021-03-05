-- This file is public domain, it can be freely copied without restrictions.
-- SPDX-License-Identifier: CC0-1.0

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

package matrix_multiplier_pkg is

    -- VHDL-2008 required for unconstrained array types
    type flat_matrix_type is array (integer range <>) of unsigned;

    function clog2(n : positive) return natural;

end package;

package body matrix_multiplier_pkg is

    function clog2(n : positive) return natural is
    begin
        return integer(ceil(log2(real(n))));
    end function;

end package body;
