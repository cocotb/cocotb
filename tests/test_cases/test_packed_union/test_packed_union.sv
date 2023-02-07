/**
 * Copyright cocotb contributors
 * Licensed under the Revised BSD License, see LICENSE for details.
 * SPDX-License-Identifier: BSD-3-Clause
*/

module test_packed_union
    (input union packed {
           logic [3:0] a;
           logic [1:0][1:0] b;
     } t);
endmodule : test_packed_union
