// Copyright (c) 2016 Technische Universitaet Dresden, Germany
// Chair for VLSI-Design, Diagnostic and Architecture
// Author: Martin Zabel
// All rights reserved.
//
// A simple D flip-flop

module dff (c,d,q);
   input wire c, d;
   output reg q = 1'b0;

   always @(posedge c)
     begin
	q <= #1 d;
     end
   
endmodule // dff
