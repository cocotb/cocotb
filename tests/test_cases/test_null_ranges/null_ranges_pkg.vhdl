-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause


library ieee;

use ieee.numeric_std.all;

package null_ranges_pkg is

    type unsignedArrayType is array (natural range <>) of unsigned(7 downto 0);

end package null_ranges_pkg;

package body null_ranges_pkg is
end package body null_ranges_pkg;
