/****************************************************************************
 * rv_data_monitor_bfm.sv
 ****************************************************************************/

/**
 * Module: rv_data_monitor_bfm
 * 
 * TODO: Add module documentation
 */
module rv_data_monitor_bfm #(
		parameter DATA_WIDTH = 8
		) (
			input						clock,
			input						reset,
			input[DATA_WIDTH-1:0]		data,
			input						data_valid,
			input						data_ready
		);
	
	reg[DATA_WIDTH-1:0]		data_v = 0;
	reg						data_valid_v = 0;
	
	initial begin
		if (DATA_WIDTH > 64) begin
			$display("Error: rv_data_monitor_bfm %m -- DATA_WIDTH>64 (%0d)", DATA_WIDTH);
			$finish();
		end
	end
	
	always @(posedge clock) begin
		if (!reset && data_valid && data_ready) begin
			data_recv(data);
		end
	end
	
	// Auto-generated code to implement the BFM API
${cocotb_bfm_api_impl}

endmodule

