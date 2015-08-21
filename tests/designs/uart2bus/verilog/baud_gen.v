//---------------------------------------------------------------------------------------
// baud rate generator for uart 
//
// this module has been changed to receive the baud rate dividing counter from registers.
// the two registers should be calculated as follows:
// first register:
// 		baud_freq = 16*baud_rate / gcd(global_clock_freq, 16*baud_rate)
// second register:
// 		baud_limit = (global_clock_freq / gcd(global_clock_freq, 16*baud_rate)) - baud_freq 
//
//---------------------------------------------------------------------------------------

module baud_gen 
(
	clock, reset, 
	ce_16, baud_freq, baud_limit 
);
//---------------------------------------------------------------------------------------
// modules inputs and outputs 
input 			clock;		// global clock input 
input 			reset;		// global reset input 
output			ce_16;		// baud rate multiplyed by 16 
input	[11:0]	baud_freq;	// baud rate setting registers - see header description 
input	[15:0]	baud_limit;

// internal registers 
reg ce_16;
reg [15:0]	counter;
//---------------------------------------------------------------------------------------
// module implementation 
// baud divider counter  
always @ (posedge clock or posedge reset)
begin
	if (reset) 
		counter <= 16'b0;
	else if (counter >= baud_limit) 
		counter <= counter - baud_limit;
	else 
		counter <= counter + baud_freq;
end

// clock divider output 
always @ (posedge clock or posedge reset)
begin
	if (reset)
		ce_16 <= 1'b0;
	else if (counter >= baud_limit) 
		ce_16 <= 1'b1;
	else 
		ce_16 <= 1'b0;
end 

endmodule
//---------------------------------------------------------------------------------------
//						Th.. Th.. Th.. Thats all folks !!!
//---------------------------------------------------------------------------------------
