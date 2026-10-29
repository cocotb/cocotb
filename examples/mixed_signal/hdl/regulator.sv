// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

module regulator(input       vdd,
                 input [3:0] trim,
                 output      vout,
                 input       vss);

  regulator_block
    #(.vout_abs  (3.3),
      .trim_step (0.2))
  i_regulator_block
    (
     .vdd  (vdd),
     .trim (trim),
     .vout (vout),
     .vss  (vss)
     );

  resistor
    #(.resistance (100))
  i_resistor
    (
     .p (vout),
     .n (vss)
     );

endmodule
