`timescale 1 ps / 1 ps

module logic_testbench (
    input clk,
    input reset
);

// Normal counters
reg [15:0] unsigned_counter_little;
reg signed [16:0] signed_counter_little;
reg [0:15] unsigned_counter_big;
reg signed [0:16] signed_counter_big;

always @ (posedge clk or negedge reset) begin
    if (~reset) begin
        unsigned_counter_little <= 0;
        signed_counter_little <= 0;
        unsigned_counter_big <= 0;
        signed_counter_big <= 0;
    end else begin
        unsigned_counter_little <= unsigned_counter_little + 1;
        signed_counter_little <= signed_counter_little + 1;
        unsigned_counter_big <= unsigned_counter_big + 1;
        signed_counter_big <= signed_counter_big + 1;
    end
end

// Overflowing counters
reg [2:0] unsigned_overflow_counter_little;
reg signed [3:0] signed_overflow_counter_little;
reg [0:2] unsigned_overflow_counter_big;
reg signed [0:3] signed_overflow_counter_big;

always @ (posedge clk or negedge reset) begin
    if (~reset) begin
        unsigned_overflow_counter_little <= 0;
        signed_overflow_counter_little <= 0;
        unsigned_overflow_counter_big <= 0;
        signed_overflow_counter_big <= 0;
    end else begin
        unsigned_overflow_counter_little <= unsigned_overflow_counter_little + 1;
        signed_overflow_counter_little <= signed_overflow_counter_little + 1;
        unsigned_overflow_counter_big <= unsigned_overflow_counter_big + 1;
        signed_overflow_counter_big <= signed_overflow_counter_big + 1;
    end
end

// Truncation
wire [8:0] truncate_unsigned_little;
wire signed [9:0] truncate_signed_little;
wire [0:8] truncate_unsigned_big;
wire signed [0:9] truncate_signed_big;

assign truncate_unsigned_little = unsigned_counter_little;
assign truncate_signed_little = signed_counter_little;
assign truncate_unsigned_big = unsigned_counter_big;
assign truncate_signed_big = signed_counter_big;

// Extension
wire [8:0] extend_unsigned_little;
wire signed [9:0] extend_signed_little;
wire [0:8] extend_unsigned_big;
wire signed [0:9] extend_signed_big;

assign extend_unsigned_little = unsigned_overflow_counter_little;
assign extend_signed_little = signed_overflow_counter_little;
assign extend_unsigned_big = unsigned_overflow_counter_big;
assign extend_signed_big = signed_overflow_counter_big;

// Endian-ness swap
wire [0:15] unsigned_counter_little_to_big;
wire signed [0:16] signed_counter_little_to_big;
wire [15:0] unsigned_counter_big_to_little;
wire signed [16:0] signed_counter_big_to_little;

assign unsigned_counter_little_to_big = unsigned_counter_little;
assign signed_counter_little_to_big = signed_counter_little;
assign unsigned_counter_big_to_little = unsigned_counter_big;
assign signed_counter_big_to_little = signed_counter_big;

// Use of $signed
wire [7:0] unsigned_assigned_dollar_signed_little;
wire signed [8:0] signed_assigned_dollar_signed_little;
wire [0:7] unsigned_assigned_dollar_signed_big;
wire signed [0:8] signed_assigned_dollar_signed_big;

assign unsigned_assigned_dollar_signed_little = $signed(-57);
assign signed_assigned_dollar_signed_little = $signed(-57);
assign unsigned_assigned_dollar_signed_big = $signed(-57);
assign signed_assigned_dollar_signed_big = $signed(-57);

// Waves
initial begin
    $dumpfile("waveform.vcd");
    $dumpvars(0, logic_testbench);
end

endmodule
