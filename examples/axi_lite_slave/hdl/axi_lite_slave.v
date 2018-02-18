/*
Distributed under the MIT license.
Copyright (c) 2017 Dave McCoy (dave.mccoy@cospandesign.com)

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
 * Author: David McCoy (dave.mccoy@cospandesign.com)
 * Description: An AXI Lite Slave interface that simplifies register access
 *  XXX: Currently there is no strobe level access
 *
 * Changes:
 *  3/24/2017: Initial Commit
 */

`timescale 1ps / 1ps

`include "axi_defines.v"

module axi_lite_slave #(
  parameter ADDR_WIDTH          = 32,
  parameter DATA_WIDTH          = 32,
  parameter STROBE_WIDTH        = (DATA_WIDTH / 8)

)(

  input                               clk,
  input                               rst,

  //Write Address Channel
  input                               i_awvalid,
  input       [ADDR_WIDTH - 1: 0]     i_awaddr,
  output  reg                         o_awready,

  //Write Data Channel
  input                               i_wvalid,
  output  reg                         o_wready,
  input       [STROBE_WIDTH - 1:0]    i_wstrb,
  input       [DATA_WIDTH - 1: 0]     i_wdata,

  //Write Response Channel
  output  reg                         o_bvalid,
  input                               i_bready,
  output  reg [1:0]                   o_bresp,

  //Read Address Channel
  input                               i_arvalid,
  output  reg                         o_arready,
  input       [ADDR_WIDTH - 1: 0]     i_araddr,

  //Read Data Channel
  output  reg                         o_rvalid,
  input                               i_rready,
  output  reg [1:0]                   o_rresp,
  output  reg [DATA_WIDTH - 1: 0]     o_rdata,



  //Simple User Interface
  output  reg                         o_reg_in_rdy,
  input                               i_reg_in_ack_stb,
  output  reg [ADDR_WIDTH - 1: 0]     o_reg_address,
  output  reg [DATA_WIDTH - 1: 0]     o_reg_in_data,

  output  reg                         o_reg_out_req,
  input                               i_reg_out_rdy_stb,
  input       [DATA_WIDTH - 1: 0]     i_reg_out_data,
  input                               i_reg_invalid_addr

);



//local parameters
localparam      IDLE                = 4'h0;
localparam      RECEIVE_WRITE_DATA  = 4'h1;
localparam      WRITE_WAIT_FOR_USER = 4'h2;
localparam      SEND_WRITE_RESP     = 4'h3;
localparam      READ_WAIT_FOR_USER  = 4'h4;
localparam      SEND_READ_DATA      = 4'h5;

//registes/wires
reg   [3:0]                           state = IDLE;

//submodules
//asynchronous logic
//synchronous logic

always @ (posedge clk) begin
  //Deassert Strobes
  if (rst) begin
    o_reg_address       <=  0;
    o_arready           <=  0;
    o_awready           <=  0;
    o_wready            <=  0;

    o_rvalid            <=  0;
    o_rdata             <=  0;
    o_bresp             <=  0;
    o_rresp             <=  0;
    o_bvalid            <=  0;

    //Demo values
    state               <= IDLE;
    o_reg_in_rdy        <=  0;
    o_reg_in_data       <=  0;
    o_reg_out_req       <=  0;
  end
  else begin
    case (state)
      IDLE: begin
        o_reg_in_rdy    <=  0;
        o_reg_address   <=  0;
        o_awready       <=  1;
        o_arready       <=  1;
        o_rvalid        <=  0;
        o_bresp         <=  0;
        o_rresp         <=  0;
        o_bvalid        <=  0;
        o_reg_out_req   <=  0;
        o_wready        <=  0;

        //Only handle read or write at one time, not both
        if (i_awvalid && o_awready) begin
          o_reg_address <=  i_awaddr;
          o_wready      <=  1;
          o_arready     <=  0;
          state         <=  RECEIVE_WRITE_DATA;
        end
        else if (i_arvalid && o_arready) begin
          o_reg_address <=  i_araddr;
          o_awready     <=  0;
          o_reg_out_req <=  1;
          state         <=  READ_WAIT_FOR_USER;
        end
      end
      RECEIVE_WRITE_DATA: begin
        o_awready       <=  0;

        if (i_wvalid) begin
          //Assume everything is okay unless the o_reg_address is wrong,
          //We don't want to clutter our states with this statement over and over again
          o_reg_in_data   <=  i_wdata;
          state           <=  WRITE_WAIT_FOR_USER;
          o_reg_in_rdy    <=  1;
        end
      end
      WRITE_WAIT_FOR_USER: begin
        //Wait for the user to ackknowledge the new info, user can introduce a delay
        if (i_reg_in_ack_stb) begin
          state           <=  SEND_WRITE_RESP;
          o_reg_in_rdy    <=  0;
          o_bvalid        <=  1;
          if (i_reg_invalid_addr) begin
            o_bresp       <=  `AXI_RESP_DECERR;
          end
          else begin
            o_bresp       <=  `AXI_RESP_OKAY;
          end
        end
      end
      SEND_WRITE_RESP: begin
        if (i_bready && o_bvalid) begin
          o_bvalid      <=  0;
          state         <=  IDLE;
        end
      end

      //Read Path
      READ_WAIT_FOR_USER: begin
        o_arready       <=  0;
        if (i_reg_out_rdy_stb) begin
          //The data in i_reg_out_data should be valid now
          o_rdata       <=  i_reg_out_data;
          if (i_reg_invalid_addr) begin
            o_rresp     <=  `AXI_RESP_DECERR;
          end
          else begin
            o_rresp     <=  `AXI_RESP_OKAY;
          end
          o_rvalid      <=  1;
          state         <=  SEND_READ_DATA;
        end
      end
      SEND_READ_DATA: begin
        //If more time is needed for a response another state should be added here
        if (i_rready && o_rvalid) begin
          o_rvalid      <=  0;
          state         <=  IDLE;
        end
      end
      default: begin
        $display("AXI Lite Slave: Shouldn't have gotten here!");
      end
    endcase
  end
end



endmodule
