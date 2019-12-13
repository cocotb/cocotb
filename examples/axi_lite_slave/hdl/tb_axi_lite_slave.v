`timescale 1ns/1ps


module tb_axi_lite_slave #(
  parameter ADDR_WIDTH          = 32,
  parameter DATA_WIDTH          = 32,
  parameter STROBE_WIDTH        = (DATA_WIDTH / 8)
)(

input                               clk,
input                               rst,

//Write Address Channel
input                               AXIML_AWVALID,
input       [ADDR_WIDTH - 1: 0]     AXIML_AWADDR,
output                              AXIML_AWREADY,

//Write Data Channel
input                               AXIML_WVALID,
output                              AXIML_WREADY,
input       [STROBE_WIDTH - 1:0]    AXIML_WSTRB,
input       [DATA_WIDTH - 1: 0]     AXIML_WDATA,

//Write Response Channel
output                              AXIML_BVALID,
input                               AXIML_BREADY,
output      [1:0]                   AXIML_BRESP,

//Read Address Channel
input                               AXIML_ARVALID,
output                              AXIML_ARREADY,
input       [ADDR_WIDTH - 1: 0]     AXIML_ARADDR,

//Read Data Channel
output                              AXIML_RVALID,
input                               AXIML_RREADY,
output      [1:0]                   AXIML_RRESP,
output      [DATA_WIDTH - 1: 0]     AXIML_RDATA

);


//Local Parameters
//Registers

reg               r_rst;
reg [7:0] 	  test_id         = 0;

//Workaround for weird icarus simulator bug
always @ (*)      r_rst           = rst;

//submodules
axi_lite_demo #(
  .ADDR_WIDTH   (ADDR_WIDTH     ),
  .DATA_WIDTH   (DATA_WIDTH     )
) dut (
  .clk          (clk            ),
  .rst          (r_rst          ),


  .i_awvalid    (AXIML_AWVALID  ),
  .i_awaddr     (AXIML_AWADDR   ),
  .o_awready    (AXIML_AWREADY  ),


  .i_wvalid     (AXIML_WVALID   ),
  .o_wready     (AXIML_WREADY   ),
  .i_wstrb      (AXIML_WSTRB    ),
  .i_wdata      (AXIML_WDATA    ),


  .o_bvalid     (AXIML_BVALID   ),
  .i_bready     (AXIML_BREADY   ),
  .o_bresp      (AXIML_BRESP    ),


  .i_arvalid    (AXIML_ARVALID  ),
  .o_arready    (AXIML_ARREADY  ),
  .i_araddr     (AXIML_ARADDR   ),


  .o_rvalid     (AXIML_RVALID   ),
  .i_rready     (AXIML_RREADY   ),
  .o_rresp      (AXIML_RRESP    ),
  .o_rdata      (AXIML_RDATA    )

);

//asynchronus logic
//synchronous logic

`ifndef VERILATOR // traced differently
  initial begin
    $dumpfile ("design.vcd");
    $dumpvars(0, tb_axi_lite_slave);
  end
`endif

endmodule
