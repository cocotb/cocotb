//---------------------------------------------------------------------------------------
// uart parser module  
//
//---------------------------------------------------------------------------------------

module uart_parser 
(
	// global signals 
	clock, reset,
	// transmit and receive internal interface signals from uart interface 
	rx_data, new_rx_data, 
	tx_data, new_tx_data, tx_busy, 
	// internal bus to register file 
	int_address, int_wr_data, int_write,
	int_rd_data, int_read, 
	int_req, int_gnt 
);
//---------------------------------------------------------------------------------------
// parameters 
parameter		AW = 8;			// address bus width parameter 

// modules inputs and outputs 
input 			clock;			// global clock input 
input 			reset;			// global reset input 
output	[7:0]	tx_data;		// data byte to transmit 
output			new_tx_data;	// asserted to indicate that there is a new data byte for
								// transmission 
input 			tx_busy;		// signs that transmitter is busy 
input	[7:0]	rx_data;		// data byte received 
input 			new_rx_data;	// signs that a new byte was received 
output	[AW-1:0] int_address;	// address bus to register file 
output	[7:0]	int_wr_data;	// write data to register file 
output			int_write;		// write control to register file 
output			int_read;		// read control to register file 
input	[7:0]	int_rd_data;	// data read from register file 
output			int_req;		// bus access request signal 
input			int_gnt;		// bus access grant signal 

// registered outputs
reg	[7:0] tx_data;
reg new_tx_data;
reg	[AW-1:0] int_address;
reg	[7:0] int_wr_data;
reg write_req, read_req, int_write, int_read;

// internal constants 
// define characters used by the parser 
`define CHAR_CR			8'h0d
`define CHAR_LF			8'h0a
`define CHAR_SPACE		8'h20
`define CHAR_TAB		8'h09
`define CHAR_COMMA		8'h2C
`define CHAR_R_UP		8'h52
`define CHAR_r_LO		8'h72
`define CHAR_W_UP		8'h57
`define CHAR_w_LO		8'h77
`define CHAR_0			8'h30
`define CHAR_1			8'h31
`define CHAR_2			8'h32
`define CHAR_3			8'h33
`define CHAR_4			8'h34
`define CHAR_5			8'h35
`define CHAR_6			8'h36
`define CHAR_7			8'h37
`define CHAR_8			8'h38
`define CHAR_9			8'h39
`define CHAR_A_UP		8'h41
`define CHAR_B_UP		8'h42
`define CHAR_C_UP		8'h43
`define CHAR_D_UP		8'h44
`define CHAR_E_UP		8'h45
`define CHAR_F_UP		8'h46
`define CHAR_a_LO		8'h61
`define CHAR_b_LO		8'h62
`define CHAR_c_LO		8'h63
`define CHAR_d_LO		8'h64
`define CHAR_e_LO		8'h65
`define CHAR_f_LO		8'h66

// main (receive) state machine states 
`define MAIN_IDLE		4'b0000
`define MAIN_WHITE1		4'b0001
`define MAIN_DATA		4'b0010
`define MAIN_WHITE2		4'b0011
`define MAIN_ADDR		4'b0100
`define MAIN_EOL		4'b0101
// binary mode extension states 
`define MAIN_BIN_CMD	4'b1000
`define MAIN_BIN_ADRH	4'b1001
`define MAIN_BIN_ADRL	4'b1010
`define MAIN_BIN_LEN    4'b1011
`define MAIN_BIN_DATA   4'b1100 

// transmit state machine 
`define TX_IDLE			3'b000
`define TX_HI_NIB		3'b001
`define TX_LO_NIB		3'b100
`define TX_CHAR_CR		3'b101
`define TX_CHAR_LF		3'b110

// binary extension mode commands - the command is indicated by bits 5:4 of the command byte 
`define BIN_CMD_NOP		2'b00
`define BIN_CMD_READ	2'b01
`define BIN_CMD_WRITE	2'b10

// internal wires and registers 
reg [3:0] main_sm;			// main state machine 
reg read_op;				// read operation flag 
reg write_op;				// write operation flag 
reg data_in_hex_range;		// indicates that the received data is in the range of hex number 
reg [7:0] data_param;		// operation data parameter 
reg [15:0] addr_param;		// operation address parameter 
reg [3:0] data_nibble;		// data nibble from received character 
reg read_done;				// internally generated read done flag 
reg read_done_s;			// sampled read done 
reg [7:0] read_data_s;		// sampled read data 
reg [3:0] tx_nibble;		// nibble value for transmission 
reg [7:0] tx_char;			// transmit byte from nibble to character conversion 
reg [2:0] tx_sm;			// transmit state machine 
reg s_tx_busy;				// sampled tx_busy for falling edge detection 
reg bin_read_op;			// binary mode read operation flag 
reg bin_write_op;			// binary mode write operation flag 
reg addr_auto_inc;			// address auto increment mode 
reg send_stat_flag;			// send status flag 
reg [7:0] bin_byte_count;	// binary mode byte counter 
wire bin_last_byte;			// last byte flag indicates that the current byte in the command is the last 
wire tx_end_p;				// transmission end pulse 

//---------------------------------------------------------------------------------------
// module implementation 
// main state machine 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		main_sm <= `MAIN_IDLE;
	else if (new_rx_data) 
	begin 
		case (main_sm)
			// wait for a read ('r') or write ('w') command 
			// binary extension - an all zeros byte enabled binary commands 
			`MAIN_IDLE:
				// check received character 
				if (rx_data == 8'h0)
					// an all zeros received byte enters binary mode 
					main_sm <= `MAIN_BIN_CMD;
				else if ((rx_data == `CHAR_r_LO) | (rx_data == `CHAR_R_UP))
					// on read wait to receive only address field 
					main_sm <= `MAIN_WHITE2;
				else if ((rx_data == `CHAR_w_LO) | (rx_data == `CHAR_W_UP))
					// on write wait to receive data and address 
					main_sm <= `MAIN_WHITE1;
				else if ((rx_data == `CHAR_CR) | (rx_data == `CHAR_LF))
					// on new line sta in idle 
					main_sm <= `MAIN_IDLE;
				else 
					// any other character wait to end of line (EOL)
					main_sm <= `MAIN_EOL;
				
			// wait for white spaces till first data nibble 
			`MAIN_WHITE1:
				// wait in this case until any white space character is received. in any 
				// valid character for data value switch to data state. a new line or carriage 
				// return should reset the state machine to idle.
				// any other character transitions the state machine to wait for EOL.
				if ((rx_data == `CHAR_SPACE) | (rx_data == `CHAR_TAB))
					main_sm <= `MAIN_WHITE1;
				else if (data_in_hex_range)
					main_sm <= `MAIN_DATA;
				else if ((rx_data == `CHAR_CR) | (rx_data == `CHAR_LF))
					main_sm <= `MAIN_IDLE;
				else 
					main_sm <= `MAIN_EOL;
					
			// receive data field 
			`MAIN_DATA:
				// wait while data in hex range. white space transition to wait white 2 state.
				// CR and LF resets the state machine. any other value cause state machine to 
				// wait til end of line.
				if (data_in_hex_range)
					main_sm <= `MAIN_DATA;
				else if ((rx_data == `CHAR_SPACE) | (rx_data == `CHAR_TAB))
					main_sm <= `MAIN_WHITE2;
				else if ((rx_data == `CHAR_CR) | (rx_data == `CHAR_LF))
					main_sm <= `MAIN_IDLE;
				else 
					main_sm <= `MAIN_EOL;
				
			// wait for white spaces till first address nibble 
			`MAIN_WHITE2:
				// similar to MAIN_WHITE1 
				if ((rx_data == `CHAR_SPACE) | (rx_data == `CHAR_TAB))
					main_sm <= `MAIN_WHITE2;
				else if (data_in_hex_range)
					main_sm <= `MAIN_ADDR;
				else if ((rx_data == `CHAR_CR) | (rx_data == `CHAR_LF))
					main_sm <= `MAIN_IDLE;
				else 
					main_sm <= `MAIN_EOL;

			// receive address field 
			`MAIN_ADDR:
				// similar to MAIN_DATA 
				if (data_in_hex_range)
					main_sm <= `MAIN_ADDR;
				else if ((rx_data == `CHAR_CR) | (rx_data == `CHAR_LF))
					main_sm <= `MAIN_IDLE;
				else 
					main_sm <= `MAIN_EOL;

			// wait to EOL 				
			`MAIN_EOL:
				// wait for CR or LF to move back to idle 
				if ((rx_data == `CHAR_CR) | (rx_data == `CHAR_LF))
					main_sm <= `MAIN_IDLE;
					
			// binary extension 
			// wait for command - one byte 
			`MAIN_BIN_CMD:
				// check if command is a NOP command 
				if (rx_data[5:4] == `BIN_CMD_NOP)
					// if NOP command then switch back to idle state 
					main_sm <= `MAIN_IDLE;
				else 
					// not a NOP command, continue receiving parameters 
					main_sm <= `MAIN_BIN_ADRH;
							
			// wait for address parameter - two bytes 
			// high address byte 
			`MAIN_BIN_ADRH:
				// switch to next state 
				main_sm <= `MAIN_BIN_ADRL;
			
			// low address byte 
			`MAIN_BIN_ADRL:
				// switch to next state 
				main_sm <= `MAIN_BIN_LEN;
			
			// wait for length parameter - one byte 
			`MAIN_BIN_LEN:
				// check if write command else command reception ended 
				if (bin_write_op)
					// wait for write data 
					main_sm <= `MAIN_BIN_DATA;
				else 
					// command reception has ended 
					main_sm <= `MAIN_IDLE;
			
			// on write commands wait for data till end of buffer as specified by length parameter 
			`MAIN_BIN_DATA:
				// if this is the last data byte then return to idle 
				if (bin_last_byte)
					main_sm <= `MAIN_IDLE;
				
			// go to idle 
			default:
				main_sm <= `MAIN_IDLE;
		endcase 
	end 
end 

// indicates that the received data is in the range of hex number 
always @ (rx_data)
begin 
	if (((rx_data >= `CHAR_0   ) && (rx_data <= `CHAR_9   )) || 
	    ((rx_data >= `CHAR_A_UP) && (rx_data <= `CHAR_F_UP)) || 
	    ((rx_data >= `CHAR_a_LO) && (rx_data <= `CHAR_f_LO)))
		data_in_hex_range <= 1'b1;
	else 
		data_in_hex_range <= 1'b0;
end 

// read operation flag 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		read_op <= 1'b0;
	else if ((main_sm == `MAIN_IDLE) && new_rx_data) 
	begin 
		// the read operation flag is set when a read command is received in idle state and cleared 
		// if any other character is received during that state.
		if ((rx_data == `CHAR_r_LO) | (rx_data == `CHAR_R_UP))
			read_op <= 1'b1;
		else 
			read_op <= 1'b0;
	end 
end 

// write operation flag 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		write_op <= 1'b0;
	else if ((main_sm == `MAIN_IDLE) & new_rx_data) 
	begin 
		// the write operation flag is set when a write command is received in idle state and cleared 
		// if any other character is received during that state.
		if ((rx_data == `CHAR_w_LO) | (rx_data == `CHAR_W_UP))
			write_op <= 1'b1;
		else 
			write_op <= 1'b0;
	end 
end 

// binary mode read operation flag 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		bin_read_op <= 1'b0;
	else if ((main_sm == `MAIN_BIN_CMD) && new_rx_data && (rx_data[5:4] == `BIN_CMD_READ))
		// read command is started on reception of a read command 
		bin_read_op <= 1'b1;
	else if (bin_read_op && tx_end_p && bin_last_byte)
		// read command ends on transmission of the last byte read 
		bin_read_op <= 1'b0;
end 

// binary mode write operation flag 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		bin_write_op <= 1'b0;
	else if ((main_sm == `MAIN_BIN_CMD) && new_rx_data && (rx_data[5:4] == `BIN_CMD_WRITE))
		// write command is started on reception of a write command 
		bin_write_op <= 1'b1;
	else if ((main_sm == `MAIN_BIN_DATA) && new_rx_data && bin_last_byte)
		bin_write_op <= 1'b0;
end 

// send status flag - used only in binary extension mode 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		send_stat_flag <= 1'b0;
	else if ((main_sm == `MAIN_BIN_CMD) && new_rx_data)
	begin 
		// check if a status byte should be sent at the end of the command 
		if (rx_data[0] == 1'b1)
			send_stat_flag <= 1'b1;
		else 
			send_stat_flag <= 1'b0;
	end 
end 

// address auto increment - used only in binary extension mode 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		addr_auto_inc <= 1'b0;
	else if ((main_sm == `MAIN_BIN_CMD) && new_rx_data)
	begin 
		// check if address should be automatically incremented or not. 
		// Note that when rx_data[1] is set, address auto increment is disabled. 
		if (rx_data[1] == 1'b0)
			addr_auto_inc <= 1'b1;
		else 
			addr_auto_inc <= 1'b0;
	end 
end 

// operation data parameter 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		data_param <= 8'h0;
	else if ((main_sm == `MAIN_WHITE1) & new_rx_data & data_in_hex_range) 
		data_param <= {4'h0, data_nibble};
	else if ((main_sm == `MAIN_DATA) & new_rx_data & data_in_hex_range) 
		data_param <= {data_param[3:0], data_nibble};
end 

// operation address parameter 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		addr_param <= 0;
	else if ((main_sm == `MAIN_WHITE2) & new_rx_data & data_in_hex_range) 
		addr_param <= {12'b0, data_nibble};
	else if ((main_sm == `MAIN_ADDR) & new_rx_data & data_in_hex_range) 
		addr_param <= {addr_param[11:0], data_nibble};
	// binary extension 
	else if (main_sm == `MAIN_BIN_ADRH)
		addr_param[15:8] <= rx_data;
	else if (main_sm == `MAIN_BIN_ADRL)
		addr_param[7:0] <= rx_data;
end 

// binary mode command byte counter is loaded with the length parameter and counts down to zero.
// NOTE: a value of zero for the length parameter indicates a command of 256 bytes.
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		bin_byte_count <= 8'b0;
	else if ((main_sm == `MAIN_BIN_LEN) && new_rx_data)
		bin_byte_count <= rx_data;
	else if ((bin_write_op && (main_sm == `MAIN_BIN_DATA) && new_rx_data) || 
			 (bin_read_op && tx_end_p))
		// byte counter is updated on every new data received in write operations and for every 
		// byte transmitted for read operations.
		bin_byte_count <= bin_byte_count - 1;
end 
// last byte in command flag 
assign bin_last_byte = (bin_byte_count == 8'h01) ? 1'b1 : 1'b0;

// internal write control and data 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
	begin 
		write_req <= 1'b0;
		int_write <= 1'b0;
		int_wr_data <= 0;
	end 
	else if (write_op && (main_sm == `MAIN_ADDR) && new_rx_data && !data_in_hex_range)
	begin 
		write_req <= 1'b1;
		int_wr_data <= data_param;
	end 
	// binary extension mode 
	else if (bin_write_op && (main_sm == `MAIN_BIN_DATA) && new_rx_data) 
	begin 
		write_req <= 1'b1;
		int_wr_data <= rx_data;
	end 
	else if (int_gnt && write_req) 
	begin 
		// set internal bus write and clear the write request flag 
		int_write <= 1'b1;
		write_req <= 1'b0;
	end 
	else 
		int_write <= 1'b0;
end 

// internal read control 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
	begin 
		int_read <= 1'b0;
		read_req <= 1'b0;
	end 
	else if (read_op && (main_sm == `MAIN_ADDR) && new_rx_data && !data_in_hex_range)
		read_req <= 1'b1;
	// binary extension 
	else if (bin_read_op && (main_sm == `MAIN_BIN_LEN) && new_rx_data)
		// the first read request is issued on reception of the length byte 
		read_req <= 1'b1;
	else if (bin_read_op && tx_end_p && !bin_last_byte)
		// the next read requests are issued after the previous read value was transmitted and 
		// this is not the last byte to be read.
		read_req <= 1'b1;
	else if (int_gnt && read_req) 
	begin 
		// set internal bus read and clear the read request flag 
		int_read <= 1'b1;
		read_req <= 1'b0;
	end 
	else 
		int_read <= 1'b0;
end 

// external request signal is active on read or write request 
assign int_req = write_req | read_req;

// internal address 
always @ (posedge clock or posedge reset)
begin
	if (reset) 
		int_address <= 0;
	else if ((main_sm == `MAIN_ADDR) && new_rx_data && !data_in_hex_range)
		int_address <= addr_param[AW-1:0];
	// binary extension 
	else if ((main_sm == `MAIN_BIN_LEN) && new_rx_data)
		// sample address parameter on reception of length byte 
		int_address <= addr_param[AW-1:0];
	else if (addr_auto_inc && 
			 ((bin_read_op && tx_end_p && !bin_last_byte) || 
			  (bin_write_op && int_write)))
		// address is incremented on every read or write if enabled 
		int_address <= int_address + 1;
end 

// read done flag and sampled data read 
always @ (posedge clock or posedge reset)
begin
	if (reset) begin 
		read_done <= 1'b0;
		read_done_s <= 1'b0;
		read_data_s <= 8'h0;
	end 
	else 
	begin 
		// read done flag 
		if (int_read) 
			read_done <= 1'b1;
		else 
			read_done <= 1'b0;
			
		// sampled read done 
		read_done_s <= read_done;
		
		// sampled data read 
		if (read_done)
			read_data_s <= int_rd_data;
	end 
end 

// transmit state machine and control 
always @ (posedge clock or posedge reset)
begin 
	if (reset) begin 
		tx_sm <= `TX_IDLE;
		tx_data <= 8'h0;
		new_tx_data <= 1'b0;
	end 
	else 
		case (tx_sm)
			// wait for read done indication 
			`TX_IDLE: 
				// on end of every read operation check how the data read should be transmitted 
				// according to read type: ascii or binary.
				if (read_done_s) 
					// on binary mode read transmit byte value 
					if (bin_read_op)
					begin 
						// note that there is no need to change state 
						tx_data <= read_data_s;
						new_tx_data <= 1'b1;
					end 
					else 
					begin 
						tx_sm <= `TX_HI_NIB;
						tx_data <= tx_char;
						new_tx_data <= 1'b1;
					end 
				// check if status byte should be transmitted 
				else if ((send_stat_flag && bin_read_op && tx_end_p && bin_last_byte) ||	// end of read command 
					(send_stat_flag && bin_write_op && new_rx_data && bin_last_byte) ||	// end of write command 
					((main_sm == `MAIN_BIN_CMD) && new_rx_data && (rx_data[5:4] == `BIN_CMD_NOP)))	// NOP 
				begin 
					// send status byte - currently a constant 
					tx_data <= 8'h5a;
					new_tx_data <= 1'b1;
				end 
				else 
					new_tx_data <= 1'b0;

			// wait for transmit to end 
			`TX_HI_NIB:	
				if (tx_end_p) 
				begin 
					tx_sm <= `TX_LO_NIB;
					tx_data <= tx_char;
					new_tx_data <= 1'b1;
				end 
				else 
					new_tx_data <= 1'b0;
					
			// wait for transmit to end 
			`TX_LO_NIB:	
				if (tx_end_p) 
				begin 
					tx_sm <= `TX_CHAR_CR;
					tx_data <= `CHAR_CR;
					new_tx_data <= 1'b1;
				end 
				else 
					new_tx_data <= 1'b0;
					
			// wait for transmit to end 
			`TX_CHAR_CR:	
				if (tx_end_p) 
				begin 
					tx_sm <= `TX_CHAR_LF;
					tx_data <= `CHAR_LF;
					new_tx_data <= 1'b1;
				end 
				else 
					new_tx_data <= 1'b0;
					
			// wait for transmit to end 
			`TX_CHAR_LF:	
				begin 
					if (tx_end_p) 
						tx_sm <= `TX_IDLE;
					// clear tx new data flag 
					new_tx_data <= 1'b0;
				end 
					
			// return to idle 
			default:
				tx_sm <= `TX_IDLE;
		endcase 
end 

// select the nibble to the nibble to character conversion 
always @ (tx_sm or read_data_s)
begin 
	case (tx_sm)
		`TX_IDLE:		tx_nibble = read_data_s[7:4];
		`TX_HI_NIB:		tx_nibble = read_data_s[3:0];
		default:		tx_nibble = read_data_s[7:4];
	endcase
end 

// sampled tx_busy 
always @ (posedge clock or posedge reset)
begin 
	if (reset)
		s_tx_busy <= 1'b0;
	else 
		s_tx_busy <= tx_busy;
end 
// tx end pulse 
assign tx_end_p = ~tx_busy & s_tx_busy;

// character to nibble conversion 
always @ (rx_data)
begin 
	case (rx_data) 
		`CHAR_0:				data_nibble = 4'h0;
		`CHAR_1:				data_nibble = 4'h1;
		`CHAR_2:				data_nibble = 4'h2;
		`CHAR_3:				data_nibble = 4'h3;
		`CHAR_4:				data_nibble = 4'h4;
		`CHAR_5:				data_nibble = 4'h5;
		`CHAR_6:				data_nibble = 4'h6;
		`CHAR_7:				data_nibble = 4'h7;
		`CHAR_8:				data_nibble = 4'h8;
		`CHAR_9:				data_nibble = 4'h9;
		`CHAR_A_UP, `CHAR_a_LO:	data_nibble = 4'ha;
		`CHAR_B_UP, `CHAR_b_LO:	data_nibble = 4'hb;
		`CHAR_C_UP, `CHAR_c_LO:	data_nibble = 4'hc;
		`CHAR_D_UP, `CHAR_d_LO:	data_nibble = 4'hd;
		`CHAR_E_UP, `CHAR_e_LO:	data_nibble = 4'he;
		`CHAR_F_UP, `CHAR_f_LO:	data_nibble = 4'hf;
		default:				data_nibble = 4'hf;
	endcase 
end 

// nibble to character conversion 
always @ (tx_nibble)
begin 
	case (tx_nibble)
		4'h0:	tx_char = `CHAR_0;
		4'h1:	tx_char = `CHAR_1;
		4'h2:	tx_char = `CHAR_2;
		4'h3:	tx_char = `CHAR_3;
		4'h4:	tx_char = `CHAR_4;
		4'h5:	tx_char = `CHAR_5;
		4'h6:	tx_char = `CHAR_6;
		4'h7:	tx_char = `CHAR_7;
		4'h8:	tx_char = `CHAR_8;
		4'h9:	tx_char = `CHAR_9;
		4'ha:	tx_char = `CHAR_A_UP;
		4'hb:	tx_char = `CHAR_B_UP;
		4'hc:	tx_char = `CHAR_C_UP;
		4'hd:	tx_char = `CHAR_D_UP;
		4'he:	tx_char = `CHAR_E_UP;
		default: tx_char = `CHAR_F_UP;
	endcase 
end 

endmodule
//---------------------------------------------------------------------------------------
//						Th.. Th.. Th.. Thats all folks !!!
//---------------------------------------------------------------------------------------
