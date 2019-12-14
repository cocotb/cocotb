//-----------------------------------------------------------------------------
// Copyright cocotb contributors
// Licensed under the Revised BSD License, see LICENSE for details.
// SPDX-License-Identifier: BSD-3-Clause
//-----------------------------------------------------------------------------

module rv_bfm_top;
	reg clock = 0;

	always #10 clock = ~clock;

	reg reset = 1;
	reg [7:0] reset_cnt = 0;

	always @(posedge clock) begin
		if (reset_cnt == 10) begin
			reset <= 0;
		end else begin
			reset_cnt <= reset_cnt + 1;
		end
	end
	
	wire[31:0]			data;
	wire				data_valid;
	wire				data_ready;
	
	rv_data_out_bfm #(32) u_dut (
			.clock(clock),
			.reset(reset),
			.data(data),
			.data_valid(data_valid),
			.data_ready(data_ready)
		);
	
	rv_data_monitor_bfm #(32) u_mon (
			.clock(clock),
			.reset(reset),
			.data(data),
			.data_valid(data_valid),
			.data_ready(data_ready)
		);

	reg[7:0]			delay_count;
	reg[1:0]			state;
	assign data_ready = (state == 1 && delay_count == 0);
	
	always @(posedge clock) begin
		if (reset) begin
			delay_count <= 0;
			state <= 0;
		end else begin
			case (state)
				0: begin
					if (data_valid) begin
						delay_count <= ($random % 32);
						state <= 1;
					end
				end
				1: begin
					if (delay_count == 0) begin
						state <= 0;
					end else begin
						delay_count <= delay_count - 1;
					end
				end
			endcase
		end
	end

`ifdef __ICARUS__
initial begin
  $dumpfile("waveform.vcd");
  $dumpvars;
end
`endif
endmodule

