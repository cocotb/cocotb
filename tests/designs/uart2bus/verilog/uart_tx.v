//---------------------------------------------------------------------------------------
// uart transmit module
//
//---------------------------------------------------------------------------------------

module uart_tx
(
	clock, reset,
	ce_16, tx_data, new_tx_data,
	ser_out, tx_busy
);
//---------------------------------------------------------------------------------------
// modules inputs and outputs
input 			clock;			// global clock input
input 			reset;			// global reset input
input			ce_16;			// baud rate multiplied by 16 - generated by baud module
input	[7:0]	tx_data;		// data byte to transmit
input			new_tx_data;	// asserted to indicate that there is a new data byte for transmission
output			ser_out;		// serial data output
output 			tx_busy;		// signs that transmitter is busy

// internal wires
wire ce_1;		// clock enable at bit rate

// internal registers
reg ser_out;
reg tx_busy;
reg [3:0]	count16;
reg [3:0]	bit_count;
reg [8:0]	data_buf;
//---------------------------------------------------------------------------------------
// module implementation
// a counter to count 16 pulses of ce_16 to generate the ce_1 pulse
always @ (posedge clock or posedge reset)
begin
	if (reset)
		count16 <= 4'b0;
	else if (tx_busy & ce_16)
		count16 <= count16 + 4'b1;
	else if (~tx_busy)
		count16 <= 4'b0;
end

// ce_1 pulse indicating output data bit should be updated
assign ce_1 = (count16 == 4'b1111) & ce_16;

// tx_busy flag
always @ (posedge clock or posedge reset)
begin
	if (reset)
		tx_busy <= 1'b0;
	else if (~tx_busy & new_tx_data)
		tx_busy <= 1'b1;
	else if (tx_busy & (bit_count == 4'h9) & ce_1)
		tx_busy <= 1'b0;
end

// output bit counter
always @ (posedge clock or posedge reset)
begin
	if (reset)
		bit_count <= 4'h0;
	else if (tx_busy & ce_1)
		bit_count <= bit_count + 4'h1;
	else if (~tx_busy)
		bit_count <= 4'h0;
end

// data shift register
always @ (posedge clock or posedge reset)
begin
	if (reset)
		data_buf <= 9'b0;
	else if (~tx_busy)
		data_buf <= {tx_data, 1'b0};
	else if (tx_busy & ce_1)
		data_buf <= {1'b1, data_buf[8:1]};
end

// output data bit
always @ (posedge clock or posedge reset)
begin
	if (reset)
		ser_out <= 1'b1;
	else if (tx_busy)
		ser_out <= data_buf[0];
	else
		ser_out <= 1'b1;
end

endmodule
//---------------------------------------------------------------------------------------
//						Th.. Th.. Th.. That's all folks !!!
//---------------------------------------------------------------------------------------
