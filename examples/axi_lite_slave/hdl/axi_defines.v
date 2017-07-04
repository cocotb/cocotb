`ifndef __AXI_DEFINES__
`define __AXI_DEFINES__

//AXI Defines

//--Burst
`define AXI_BURST_FIXED         2'b00
`define AXI_BURST_INCR          2'b01
`define AXI_BURST_WRAP          2'b10

//--Burst Size
`define AXI_BURST_SIZE_8BIT     3'b000
`define AXI_BURST_SIZE_16BIT    3'b001
`define AXI_BURST_SIZE_32BIT    3'b010
`define AXI_BURST_SIZE_64BIT    3'b011
`define AXI_BURST_SIZE_128BIT   3'b100
`define AXI_BURST_SIZE_256BIT   3'b101
`define AXI_BURST_SIZE_512BIT   3'b110
`define AXI_BURST_SIZE_1024BIT  3'b111

//--Response
`define AXI_RESP_OKAY           2'b00
`define AXI_RESP_EXOKAY         2'b01
`define AXI_RESP_SLVERR         2'b10
`define AXI_RESP_DECERR         2'b11

//--Lock
`define AXI_LOCK_NORMAL         2'b00
`define AXI_LOCK_EXCLUSIVE      2'b01
`define AXI_LOCK_LOCKED         2'b10

//--cache
//----Bufferable
`define AXI_CACHE_NON_BUF       1'b0
`define AXI_CACHE_BUF           1'b1
//----Cachable
`define AXI_CACHE_NON_CACHE     1'b0
`define AXI_CACHE_CACHE         1'b1
//----Read Allocate
`define AXI_CACHE_NON_RA        1'b0
`define AXI_CACHE_RA            1'b1
//----Write Allocate
`define AXI_CACHE_NON_WA        1'b0
`define AXI_CACHE_WA            1'b1
//----Unused
`define AXI_CACHE_UNUSED        4'b0000

//--Protection
//----ARPROT[0]
`define AXI_PROT_NORMAL         1'b0
`define AXI_PROT_PRIVLEDGE      1'b1

//----ARPROT[1]
`define AXI_PROT_SECURE         1'b0
`define AXI_PROT_NON_SECURE     1'b1

//----ARPROT[2]
`define AXI_PROT_DATA           1'b0
`define AXI_PROT_INST           1'b1

//----Unused:
`define AXI_PROT_UNUSED         {`AXI_PROT_NORMAL, `AXI_PROT_NON_SECURE, `AXI_PROT_DATA}

//--Low Power Mode
`define AXI_POWER_LOW           1'b0
`define AXI_POWER_NORMAL        1'b1

`endif //__AXI_DEFINES__
