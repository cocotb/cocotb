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

logic [7:0] queue[$] = {};

always @ (posedge clk or negedge reset) begin
    if (reset == 0) begin
        queue = {};
        asi_ready <= 1'b0;
        aso_valid <= 1'b0;
        aso_data <= 'x;
    end else begin
        asi_ready <= queue.size() < 10;
        if (asi_valid && asi_ready) begin
            queue.push_back(asi_data);
        end
        if (aso_valid && aso_ready) begin
            queue.pop_front();
        end
        aso_data <= queue[0];
        aso_valid <= queue.size() > 0;
    end
end

initial begin
     $dumpfile("waveform.vcd");
     $dumpvars;
end

endmodule : avalon_streaming
