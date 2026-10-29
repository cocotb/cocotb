// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

import nettypes_pkg::*;

module tb_regulator;

  voltage_net vdd, vss, vout;
  real vdd_val, vss_val = 0.0;
  logic signed [3:0] trim_val = 0;

  assign vdd = vdd_val;
  assign vss = vss_val;

  // the design
  regulator i_regulator (.vdd  (vdd),
                         .trim (trim_val),
                         .vout (vout),
                         .vss  (vss)
                         );

  // the "multimeter"
  analog_probe i_analog_probe ();

endmodule
