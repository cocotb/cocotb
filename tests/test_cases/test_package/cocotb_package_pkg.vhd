-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

library ieee;
use ieee.std_logic_1164.all;

package cocotb_package_pkg_1 is
    constant five_int : integer := 5;
    constant eight_logic : std_logic_vector(31 downto 0) := X"00000008";
    constant hello_string : string := "hello";
end package cocotb_package_pkg_1;

package cocotb_package_pkg_2 is
    constant eleven_int : integer := 11;
end package cocotb_package_pkg_2;
