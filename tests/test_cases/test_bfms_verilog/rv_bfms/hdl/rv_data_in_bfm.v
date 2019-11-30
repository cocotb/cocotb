/****************************************************************************
 * rv_data_in_bfm.sv
 ****************************************************************************/

/**
 * Module: rv_data_in_bfm
 * 
 * TODO: Add module documentation
 */
module rv_data_in_bfm #(
		parameter DATA_WIDTH = 8
		) (
			input						clock,
			input						reset,
			input[DATA_WIDTH-1:0]		data,
			input						data_valid,
			output						data_ready
		);
	
	// Auto-generated code to implement the BFM API
${cocotb_bfm_api_impl}

endmodule


