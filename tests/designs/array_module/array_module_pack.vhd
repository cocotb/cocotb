-------------------------------------------------------------------------------
-- Copyright (c) 2016 Potential Ventures Ltd
-- All rights reserved.
--
-- Redistribution and use in source and binary forms, with or without
-- modification, are permitted provided that the following conditions are met:
--     * Redistributions of source code must retain the above copyright
--       notice, this list of conditions and the following disclaimer.
--     * Redistributions in binary form must reproduce the above copyright
--       notice, this list of conditions and the following disclaimer in the
--       documentation and/or other materials provided with the distribution.
--     * Neither the name of Potential Ventures Ltd,
--       Copyright (c) 2013 SolarFlare Communications Inc nor the
--       names of its contributors may be used to endorse or promote products
--       derived from this software without specific prior written permission.
--
-- THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
-- ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
-- WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
-- DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
-- DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
-- (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
-- LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
-- ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
-- (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
-- SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
-------------------------------------------------------------------------------

library ieee;

use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package array_module_pack is
    type t1 is array (0 to 3) of std_logic;
    type t2 is array (7 downto 4) of std_logic_vector(7 downto 0);
    type t3 is array (natural range <>) of std_logic_vector(7 downto 0);
    type t4 is array (0 to 3) of t2;
    type t5 is array (0 to 2, 0 to 3) of std_logic_vector(7 downto 0);
    type t6 is array (natural range <>, natural range <>) of std_logic_vector(7 downto 0);

    type rec_type is record
        a : std_logic;
        b : t3(0 to 2);
    end record rec_type;
    type     rec_array is array (natural range <>) of rec_type;
    constant REC_TYPE_ZERO  : rec_type  := ('0', (others=>(others=>'0')));
    constant REC_TYPE_ONE   : rec_type  := ('1', (others=>(others=>'1')));

end package array_module_pack;

package body array_module_pack is
end package body array_module_pack;
