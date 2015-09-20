/*
  Legal Notice: (C)2007 Altera Corporation. All rights reserved.  Your
  use of Altera Corporation's design tools, logic functions and other
  software and tools, and its AMPP partner logic functions, and any
  output files any of the foregoing (including device programming or
  simulation files), and any associated documentation or information are
  expressly subject to the terms and conditions of the Altera Program
  License Subscription Agreement or other applicable license agreement,
  including, without limitation, that your use is for the sole purpose
  of programming logic devices manufactured by Altera and sold by Altera
  or its authorized distributors.  Please refer to the applicable
  agreement for further details.
*/

/*

    Author:  JCJB
    Date:  11/04/2007

    This bursting read master is passed a word aligned address, length in bytes,
    and a 'go' bit.  The master will continue to post full length bursts until
    the length register reaches a value less than a full burst.  A single final
    burst is then posted and when all the reads return the done bit will be asserted.

    To use this master you must simply drive the control signals into this block,
    and also read the data from the exposed read FIFO.  To read from the exposed FIFO
    use the 'user_read_buffer' signal to pop data from the FIFO 'user_buffer_data'.
    The signal 'user_data_available' is asserted whenever data is available from the
    exposed FIFO.

*/

// altera message_off 10230

/* altera scfifo model rewritten */
module scfifo (
        input aclr,
        input clock,
        input [31:0] data,
        output empty,
        output [31:0] q,
        input rdreq,
        input [4:0] usedw,
        input wrreq);

    localparam lpm_width = 32;
    localparam lpm_numwords = 32;
    localparam lpm_showahead = "ON";
    localparam use_eab = "ON";
    localparam add_ram_output_register = "OFF";
    localparam underflow_checking = "OFF";
    localparam overflow_checking = "OFF";

endmodule

module burst_read_master (
    clk,
    reset,

    // control inputs and outputs
    control_fixed_location,
    control_read_base,
    control_read_length,
    control_go,
    control_done,
    control_early_done,

    // user logic inputs and outputs
    user_read_buffer,
    user_buffer_data,
    user_data_available,

    // master inputs and outputs
    master_address,
    master_read,
    master_byteenable,
    master_readdata,
    master_readdatavalid,
    master_burstcount,
    master_waitrequest
);

    parameter DATAWIDTH = 32;
    parameter MAXBURSTCOUNT = 4;
    parameter BURSTCOUNTWIDTH = 3;
    parameter BYTEENABLEWIDTH = 4;
    parameter ADDRESSWIDTH = 32;
    parameter FIFODEPTH = 32;
    parameter FIFODEPTH_LOG2 = 5;
    parameter FIFOUSEMEMORY = 1;  // set to 0 to use LEs instead

    input clk;
    input reset;


    // control inputs and outputs
    input control_fixed_location;
    input [ADDRESSWIDTH-1:0] control_read_base;
    input [ADDRESSWIDTH-1:0] control_read_length;
    input control_go;
    output wire control_done;
    output wire control_early_done;  // don't use this unless you know what you are doing, it's going to fire when the last read is posted, not when the last data returns!

    // user logic inputs and outputs
    input user_read_buffer;
    output wire [DATAWIDTH-1:0] user_buffer_data;
    output wire user_data_available;

    // master inputs and outputs
    input master_waitrequest;
    input master_readdatavalid;
    input [DATAWIDTH-1:0] master_readdata;
    output wire [ADDRESSWIDTH-1:0] master_address;
    output wire master_read;
    output wire [BYTEENABLEWIDTH-1:0] master_byteenable;
    output wire [BURSTCOUNTWIDTH-1:0] master_burstcount;

    // internal control signals
    reg control_fixed_location_d1;
    wire fifo_empty;
    reg [ADDRESSWIDTH-1:0] address;
    reg [ADDRESSWIDTH-1:0] length;
    reg [FIFODEPTH_LOG2-1:0] reads_pending;
    wire increment_address;
    wire [BURSTCOUNTWIDTH-1:0] burst_count;
    wire [BURSTCOUNTWIDTH-1:0] first_short_burst_count;
    wire first_short_burst_enable;
    wire [BURSTCOUNTWIDTH-1:0] final_short_burst_count;
    wire final_short_burst_enable;
    wire [BURSTCOUNTWIDTH-1:0] burst_boundary_word_address;
    reg burst_begin;
    wire too_many_reads_pending;
    wire [FIFODEPTH_LOG2-1:0] fifo_used;



    // registering the control_fixed_location bit
    always @ (posedge clk or posedge reset)
    begin
        if (reset == 1)
        begin
            control_fixed_location_d1 <= 0;
        end
        else
        begin
            if (control_go == 1)
            begin
                control_fixed_location_d1 <= control_fixed_location;
            end
        end
    end



    // master address logic
    always @ (posedge clk or posedge reset)
    begin
        if (reset == 1)
        begin
            address <= 0;
        end
        else
        begin
            if(control_go == 1)
            begin
                address <= control_read_base;
            end
            else if((increment_address == 1) & (control_fixed_location_d1 == 0))
            begin
                address <= address + (burst_count * BYTEENABLEWIDTH);  // always performing word size accesses, increment by the burst count presented
            end
        end
    end



    // master length logic
    always @ (posedge clk or posedge reset)
    begin
        if (reset == 1)
        begin
            length <= 0;
        end
        else
        begin
            if(control_go == 1)
            begin
                length <= control_read_length;
            end
            else if(increment_address == 1)
            begin
                length <= length - (burst_count * BYTEENABLEWIDTH);  // always performing word size accesses, decrement by the burst count presented
            end
        end
    end



    // controlled signals going to the master/control ports
    assign master_address = address;
    assign master_byteenable = -1;  // all ones, always performing word size accesses
    assign master_burstcount = burst_count;
    assign control_done = (length == 0) & (reads_pending == 0);  // need to make sure that the reads have returned before firing the done bit
    assign control_early_done = (length == 0);  // advanced feature, you should use 'control_done' if you need all the reads to return first
    assign master_read = (too_many_reads_pending == 0) & (length != 0);
    assign burst_boundary_word_address = ((address / BYTEENABLEWIDTH) & (MAXBURSTCOUNT - 1));
    assign first_short_burst_enable = (burst_boundary_word_address != 0);
    assign final_short_burst_enable = (length < (MAXBURSTCOUNT * BYTEENABLEWIDTH));

    assign first_short_burst_count = ((burst_boundary_word_address & 1'b1) == 1'b1)? 1 :  // if the burst boundary isn't a multiple of 2 then must post a burst of 1 to get to a multiple of 2 for the next burst
        (((MAXBURSTCOUNT - burst_boundary_word_address) < (length / BYTEENABLEWIDTH))?
        (MAXBURSTCOUNT - burst_boundary_word_address) : (length / BYTEENABLEWIDTH));
    assign final_short_burst_count = (length / BYTEENABLEWIDTH);

    assign burst_count = (first_short_burst_enable == 1)? first_short_burst_count :  // this will get the transfer back on a burst boundary,
    (final_short_burst_enable == 1)? final_short_burst_count : MAXBURSTCOUNT;
assign increment_address = (too_many_reads_pending == 0) & (master_waitrequest == 0) & (length != 0);
assign too_many_reads_pending = (reads_pending + fifo_used) >= (FIFODEPTH - MAXBURSTCOUNT - 4);  // make sure there are fewer reads posted than room in the FIFO


// tracking FIFO
always @ (posedge clk or posedge reset)
begin
    if (reset == 1)
    begin
        reads_pending <= 0;
    end
    else
    begin
        if(increment_address == 1)
        begin
            if(master_readdatavalid == 0)
            begin
                reads_pending <= reads_pending + burst_count;
            end
            else
            begin
                reads_pending <= reads_pending + burst_count - 1;  // a burst read was posted, but a word returned
            end
        end
        else
        begin
            if(master_readdatavalid == 0)
            begin
                reads_pending <= reads_pending;  // burst read was not posted and no read returned
            end
            else
            begin
                reads_pending <= reads_pending - 1;  // burst read was not posted but a word returned
            end
        end
    end
end


// read data feeding user logic
assign user_data_available = !fifo_empty;
scfifo the_master_to_user_fifo (
    .aclr (reset),
    .clock (clk),
    .data (master_readdata),
    .empty (fifo_empty),
    .q (user_buffer_data),
    .rdreq (user_read_buffer),
    .usedw (fifo_used),
        .wrreq (master_readdatavalid)
    );
    defparam the_master_to_user_fifo.lpm_width = DATAWIDTH;
    defparam the_master_to_user_fifo.lpm_numwords = FIFODEPTH;
    defparam the_master_to_user_fifo.lpm_showahead = "ON";
    defparam the_master_to_user_fifo.use_eab = (FIFOUSEMEMORY == 1)? "ON" : "OFF";
    defparam the_master_to_user_fifo.add_ram_output_register = "OFF";
    defparam the_master_to_user_fifo.underflow_checking = "OFF";
    defparam the_master_to_user_fifo.overflow_checking = "OFF";

endmodule
