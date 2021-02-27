// This file is public domain, it can be freely copied without restrictions.
// SPDX-License-Identifier: CC0-1.0

module digital (
                input logic          clk,
                input logic [13-1:0] meas_val,
                input logic          meas_val_valid,
                output logic         pga_high_gain
                );

  timeunit 1s;
  timeprecision 1ns;

  real max_val = 2**$bits(meas_val)-1;
  real ref_val_V = 2.0;

  initial begin
    pga_high_gain = 0;  // start with low gain

    // prints %t scaled in ns (-9), with 2 precision digits,
    // and the "ns" string, last number is the minimum field width
    $timeformat(-9, 2, "ns", 11);
  end

  always @(posedge clk) begin
    if (meas_val_valid == 1) begin
      $display("%t (%M) HDL got meas_val=%0d (0x%x)", $realtime, meas_val, meas_val);

      if (pga_high_gain == 0) begin
        $display("%t (%M) PGA gain select was %0d --> calculated AFE input value back to %0f",
                 $realtime, pga_high_gain, meas_val/max_val/ 5.0 * ref_val_V);
      end else begin
        $display("%t (%M) PGA gain select was %0d --> calculated AFE input value back to %0f",
                 $realtime, pga_high_gain, meas_val/max_val/10.0 * ref_val_V);
      end

      // Automatic gain select:
      // set new gain for the next measurement
      if (meas_val > 0.7 * max_val) begin
        if (pga_high_gain == 1) begin
          $display("%t (%M) Measurement value is more than 70%% of max, switching PGA gain from 10.0 to 5.0", $realtime);
        end
        pga_high_gain = 0;
      end else if (meas_val < 0.3 * max_val) begin
        if (pga_high_gain == 0) begin
          $display("%t (%M) Measurement value is less than 30%% of max, switching PGA gain from 5.0 to 10.0", $realtime);
        end
        pga_high_gain = 1;
      end else begin
        ;  // NOP; leave gain unchanged
      end
    end // if (meas_val_valid == 1)
  end

endmodule
