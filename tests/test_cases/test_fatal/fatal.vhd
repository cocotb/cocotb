-- Copyright cocotb contributors
-- Licensed under the Revised BSD License, see LICENSE for details.
-- SPDX-License-Identifier: BSD-3-Clause

entity fatal is
end entity fatal;

architecture behav of fatal is
begin

	fatal_proc : process is
	begin
		wait for 10 ns;
		report "This is a fatal message that finishes the test" severity FAILURE;
	end process fatal_proc;

end architecture behav;
