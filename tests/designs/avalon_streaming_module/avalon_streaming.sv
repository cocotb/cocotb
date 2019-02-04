module avalon_streaming (
    input wire clk,
    input wire reset,

    input wire logic asi_valid,
    input wire logic[7:0] asi_data,
    output logic asi_ready,

    output logic aso_valid,
    output logic[7:0] aso_data,
    input wire logic aso_ready
);

logic [7:0] queue[10];
integer size;

always @ (posedge clk or negedge reset) begin
    if (reset == 0) begin
        size = 0;
        asi_ready <= 1'b0;
        aso_valid <= 1'b0;
        aso_data <= 'x;
    end else begin
        asi_ready <= size < 10;
        if (asi_valid && asi_ready) begin
            queue[size] = asi_data;
            size        = size + 1;
        end
        if (aso_valid && aso_ready) begin
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
        aso_data <= queue[0];
        aso_valid <= size > 0;
    end
end

initial begin
     $dumpfile("waveform.vcd");
     $dumpvars;
end

endmodule : avalon_streaming
