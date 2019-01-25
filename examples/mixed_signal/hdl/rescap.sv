// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

// the design-under-test
module rescap(input  interconnect vdd,
              output interconnect vout,
              input  interconnect vss);

  resistor
    #(.resistance (1e5))
  i_resistor
    (
     .p (vdd),
     .n (vout)
     );

  capacitor
    #(.capacitance (1e-12))
  i_capacitor
    (
     .p (vout),
     .n (vss)
     );

endmodule
