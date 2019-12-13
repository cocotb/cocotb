module avalon_streaming_renamed (
    input wire clk,
    input wire reset,

    input wire logic asi_VAL,
    input wire logic[7:0] asi_DAT,
    output logic asi_RDY,

    output logic aso_VAL,
    output logic[7:0] aso_DAT,
    input wire logic aso_RDY
);

logic [7:0] queue[10];
integer size;

always @ (posedge clk or negedge reset) begin
    if (reset == 0) begin
        size = 0;
        asi_RDY <= 1'b0;
        aso_VAL <= 1'b0;
        aso_DAT <= 'x;
    end else begin
        asi_RDY <= size < 10;
        if (asi_VAL && asi_RDY) begin
            queue[size] = asi_DAT;
            size        = size + 1;
        end
        if (aso_VAL && aso_RDY) begin
            queue[0]    = queue[1];
            queue[1]    = queue[2];
            queue[2]    = queue[3];
            queue[3]    = queue[4];
            queue[4]    = queue[5];
            queue[5]    = queue[6];
            queue[6]    = queue[7];
            queue[7]    = queue[8];
            queue[8]    = queue[9];
            size        = size - 1;
        end
        aso_DAT <= queue[0];
        aso_VAL <= size > 0;
    end
end

initial begin
     $dumpfile("waveform.vcd");
     $dumpvars;
end

endmodule : avalon_streaming_renamed
