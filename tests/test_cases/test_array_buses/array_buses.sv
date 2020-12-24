module array_buses
   (
      input            clk,
      input      [7:0] in_data [0:1],
      input            in_valid[0:1],
      output     [7:0] out_data [0:1],
      output           out_valid[0:1]
      );

   reg [7:0] tmp_data  [1:0];
   reg       tmp_valid [1:0];

   initial begin
      tmp_data[0] = '0;
      tmp_data[1] = '0;
      tmp_valid[0] = 1'b0;
      tmp_valid[1] = 1'b0;
   end

   always @(posedge clk) begin
      tmp_data[0] <= in_data[0];
      tmp_data[1] <= in_data[1];
      tmp_valid[0] <= in_valid[0];
      tmp_valid[1] <= in_valid[1];
   end

   assign out_data[0] = tmp_data[0];
   assign out_data[1] = tmp_data[1];
   assign out_valid[0] = tmp_valid[0];
   assign out_valid[1] = tmp_valid[1];
endmodule

