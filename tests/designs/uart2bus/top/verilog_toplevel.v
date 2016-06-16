// We simply connect two UARTs together in different languages
//
// Also define a few different structs etc. to help the testcase

module verilog_toplevel (
    input               clk,
    input               reset
);


// Verilog design
logic                   serial_v2h, serial_h2v;
logic [7:0]             verilog_rd_data, vhdl_rd_data;

typedef struct packed {
    logic [15:0]        address;
    logic [7:0]         wr_data;
    logic               read;
    logic               write;
} bus_struct_t;

bus_struct_t bus_verilog, bus_vhdl;

uart2bus_top i_verilog (
    .clock              (clk),
    .reset              (reset),

    .ser_in             (serial_h2v),
    .ser_out            (serial_v2h),

    .int_address        (bus_verilog.address),
    .int_wr_data        (bus_verilog.wr_data),
    .int_write          (bus_verilog.write),
    .int_read           (bus_verilog.read),
    .int_rd_data        (verilog_rd_data),

    .int_req            (),
    .int_gnt            ()
);

uart2BusTop i_vhdl (
    .clk                (clk),
    .clr                (reset),

    .serIn              (serial_v2h),
    .serOut             (serial_h2v),

    .intAddress         (bus_vhdl.address),
    .intWrData          (bus_vhdl.wr_data),
    .intWrite           (bus_vhdl.write),
    .intRead            (bus_vhdl.read),
    .intRdData          (vhdl_rd_data),

    .intAccessReq       (),
    .intAccessGnt       ()
);

endmodule
