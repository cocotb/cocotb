/*
Distributed under the MIT license.
Copyright (c) 2016 Dave McCoy (dave.mccoy@cospandesign.com)

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/

/*
 * Author:
 * Description:
 *
 * Changes:
 */

`timescale 1ps / 1ps

module axi_lite_demo #(
  parameter ADDR_WIDTH          = 32,
  parameter DATA_WIDTH          = 32,
  parameter STROBE_WIDTH        = (DATA_WIDTH / 8)
)(
  input                               clk,
  input                               rst,

  //Write Address Channel
  input                               i_awvalid,
  input       [ADDR_WIDTH - 1: 0]     i_awaddr,
  output                              o_awready,

  //Write Data Channel
  input                               i_wvalid,
  output                              o_wready,
  input       [STROBE_WIDTH - 1:0]    i_wstrb,
  input       [DATA_WIDTH - 1: 0]     i_wdata,

  //Write Response Channel
  output                              o_bvalid,
  input                               i_bready,
  output      [1:0]                   o_bresp,

  //Read Address Channel
  input                               i_arvalid,
  output                              o_arready,
  input       [ADDR_WIDTH - 1: 0]     i_araddr,

  //Read Data Channel
  output                              o_rvalid,
  input                               i_rready,
  output      [1:0]                   o_rresp,
  output      [DATA_WIDTH - 1: 0]     o_rdata
);
//local parameters

//Address Map
localparam  ADDR_0      = 0;
localparam  ADDR_1      = 4;

localparam  MAX_ADDR = ADDR_1;

//registers/wires

//User Interface
wire [ADDR_WIDTH - 1: 0]    w_reg_address;
reg                         r_reg_invalid_addr;

wire                        w_reg_in_rdy;
reg                         r_reg_in_ack_stb;
wire [DATA_WIDTH - 1: 0]    w_reg_in_data;

wire                        w_reg_out_req;
reg                         r_reg_out_rdy_stb;
reg [DATA_WIDTH - 1: 0]     r_reg_out_data;


//TEMP DATA, JUST FOR THE DEMO
reg [DATA_WIDTH - 1: 0]     r_temp_0;
reg [DATA_WIDTH - 1: 0]     r_temp_1;

//submodules

//Convert AXI Slave bus to a simple register/address strobe
axi_lite_slave #(
  .ADDR_WIDTH         (ADDR_WIDTH           ),
  .DATA_WIDTH         (DATA_WIDTH           )

) axi_lite_reg_interface (
  .clk                (clk                  ),
  .rst                (rst                  ),


  .i_awvalid          (i_awvalid            ),
  .i_awaddr           (i_awaddr             ),
  .o_awready          (o_awready            ),

  .i_wvalid           (i_wvalid             ),
  .o_wready           (o_wready             ),
  .i_wstrb            (i_wstrb              ),
  .i_wdata            (i_wdata              ),

  .o_bvalid           (o_bvalid             ),
  .i_bready           (i_bready             ),
  .o_bresp            (o_bresp              ),

  .i_arvalid          (i_arvalid            ),
  .o_arready          (o_arready            ),
  .i_araddr           (i_araddr             ),

  .o_rvalid           (o_rvalid             ),
  .i_rready           (i_rready             ),
  .o_rresp            (o_rresp              ),
  .o_rdata            (o_rdata              ),


  //Simple Register Interface
  .o_reg_address      (w_reg_address        ),
  .i_reg_invalid_addr (r_reg_invalid_addr   ),

  //Ingress Path (From Master)
  .o_reg_in_rdy       (w_reg_in_rdy         ),
  .i_reg_in_ack_stb   (r_reg_in_ack_stb     ),
  .o_reg_in_data      (w_reg_in_data        ),

  //Egress Path (To Master)
  .o_reg_out_req      (w_reg_out_req        ),
  .i_reg_out_rdy_stb  (r_reg_out_rdy_stb    ),
  .i_reg_out_data     (r_reg_out_data       )
);

//asynchronous logic

//synchronous logic
always @ (posedge clk) begin
  //De-assert Strobes
  r_reg_in_ack_stb                        <=  0;
  r_reg_out_rdy_stb                       <=  0;
  r_reg_invalid_addr                      <=  0;

  if (rst) begin
    r_reg_out_data                        <=  0;

    //Reset the temporary Data
    r_temp_0                              <=  0;
    r_temp_1                              <=  0;
  end
  else begin

    if (w_reg_in_rdy) begin
      //From master
      case (w_reg_address)
        ADDR_0: begin
          //$display("Incomming data on address: 0x%h: 0x%h", w_reg_address, w_reg_in_data);
          r_temp_0                        <=  w_reg_in_data;
        end
        ADDR_1: begin
          //$display("Incomming data on address: 0x%h: 0x%h", w_reg_address, w_reg_in_data);
          r_temp_1                        <=  w_reg_in_data;
        end
        default: begin
          $display ("Unknown address: 0x%h", w_reg_address);
        end
      endcase
      if (w_reg_address > MAX_ADDR) begin
        //Tell the host they wrote to an invalid address
        r_reg_invalid_addr                <= 1;
      end
      //Tell the AXI Slave Control we're done with the data
      r_reg_in_ack_stb                    <= 1;
    end
    else if (w_reg_out_req) begin
      //To master
      //$display("User is reading from address 0x%0h", w_reg_address);
      case (w_reg_address)
        ADDR_0: begin
          r_reg_out_data                  <= r_temp_0;
        end
        ADDR_1: begin
          r_reg_out_data                  <= r_temp_1;
        end
        default: begin
          //Unknown address
          r_reg_out_data                  <= 32'h00;
        end
      endcase
      if (w_reg_address > MAX_ADDR) begin
        //Tell the host they are reading from an invalid address
        r_reg_invalid_addr                <= 1;
      end
      //Tell the AXI Slave to send back this packet
      r_reg_out_rdy_stb                   <= 1;
    end
  end
end

endmodule
