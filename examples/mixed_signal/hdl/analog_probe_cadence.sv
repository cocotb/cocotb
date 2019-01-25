// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

// see also https://www.eetimes.com/document.asp?doc_id=1279150

module analog_probe;

  var string node_to_probe = "<unassigned>";

  logic probe_voltage_toggle = 0;
  real voltage;

  always @(probe_voltage_toggle) begin: probe_voltage
    if ($cds_analog_is_valid(node_to_probe, "potential")) begin
      voltage = $cds_get_analog_value(node_to_probe, "potential");
      // $display("%m: node_to_probe=%s has voltage of %e V", node_to_probe, voltage);
    end else begin
      voltage = 1.234567;
      $display("%m: Warning: node_to_probe=%s is not valid for $cds_get_analog_value, returning %f V",
               node_to_probe, voltage);
    end
  end  // probe_voltage

  logic probe_current_toggle = 0;
  real current;

  always @(probe_current_toggle) begin: probe_current
    if ($cds_analog_is_valid(node_to_probe, "flow")) begin
      current = $cds_get_analog_value(node_to_probe, "flow");
      // $display("%m: node_to_probe=%s has current of %e A", node_to_probe, current);
    end else begin
      current = 0.123456;
      $display("%m: Warning: node_to_probe=%s is not valid for $cds_get_analog_value, returning %f A",
               node_to_probe, current);
    end
  end  // probe_current

endmodule
