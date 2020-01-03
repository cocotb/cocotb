// =============================================================================
// Authors:		Martin Zabel
//
// Module:              A simple D-FF
//
// Description:
// ------------------------------------
// A simple D-FF with an initial state of '0'.
//
// License:
// =============================================================================
// Copyright 2016 Technische Universitaet Dresden - Germany
//		  Chair for VLSI-Design, Diagnostics and Architecture
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//		http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// =============================================================================

`timescale 1ns/1ps

module dff (c,d,q);
   input wire c, d;
   output reg q = 1'b0;

   always @(posedge c)
     begin
	// It is also possible to add an delay of less than one clock period
	// here.
	q <= d;
     end

endmodule // dff
