// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

package nettypes_pkg;

  nettype real voltage_net with r_res;

  function automatic real r_res(input real drivers []);
    r_res = 0.0;
    foreach(drivers[k]) r_res += drivers[k];
  endfunction

endpackage
