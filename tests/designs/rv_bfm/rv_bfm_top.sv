//-----------------------------------------------------------------------------
// Copyright (c) 2013, 2018 Potential Ventures Ltd
// Copyright (c) 2013 SolarFlare Communications Inc
// Copyright (C) 2019 Matthew Ballance
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above copyright
//       notice, this list of conditions and the following disclaimer in the
//       documentation and/or other materials provided with the distribution.
//     * Neither the name of Potential Ventures Ltd,
//       Copyright (c) 2013 SolarFlare Communications Inc nor the
//       names of its contributors may be used to endorse or promote products
//       derived from this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
// ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
// DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
// (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
// LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
// ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
// (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
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

