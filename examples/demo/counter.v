//-----------------------------------------------------------------------------
// Copyright (c) 2013 Potential Ventures Ltd
// All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//     * Redistributions of source code must retain the above copyright
//       notice, this list of conditions and the following disclaimer.
//     * Redistributions in binary form must reproduce the above copyright
//       notice, this list of conditions and the following disclaimer in the
//       documentation and/or other materials provided with the distribution.
//     * Neither the name of Potential Ventures Ltd nor the
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

//-----------------------------------------------------
// This is my second Verilog Design
// Design Name : first_counter
// File Name : first_counter.v
// Function : This is a 4 bit up-counter with
// Synchronous active high reset and
// with active high enable signal
//-----------------------------------------------------
module first_counter (
clock , // Clock input of the design
reset , // active high, synchronous Reset input
enable , // Active high enable signal for counter
counter_out, // 4 bit vector output of the counter
test_in, // test input 
test_out // test output
); // End of port list
//-------------Input Ports-----------------------------
input clock ;
input reset ;
input enable ;
input test_in ;
//-------------Output Ports----------------------------
output [3:0] counter_out ;
output test_out ;
//-------------Input ports Data Type-------------------
// By rule all the input ports should be wires   
wire clock ;
wire reset ;
wire enable ;
wire test_in ;
//-------------Output Ports Data Type------------------
// Output port can be a storage element (reg) or a wire
reg [3:0] counter_out ;
reg test_out ;

initial begin
     $dumpfile("dump.vcd");
     $dumpvars(0,first_counter);
end

//------------Code Starts Here-------------------------
// Since this counter is a positive edge trigged one,
// We trigger the below block with respect to positive
// edge of the clock.
always @ (posedge clock)
begin : COUNTER // Block Name
  // At every rising edge of clock we check if reset is active
  // If active, we load the counter output with 4'b0000
  if (reset == 1'b1) begin
    counter_out <= #1 4'b0000;
    test_out <= #1 0;
  end
  // If enable is active, then we increment the counter
  else if (enable == 1'b1) begin
    counter_out <= #1 counter_out + 1;
    test_out <= test_in;
  end
end // End of Block COUNTER

endmodule // End of Module counter
