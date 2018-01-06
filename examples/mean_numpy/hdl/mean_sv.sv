// behaviour level

module mean_sv(clk,i_dval,i_data,o_dval,o_data);

parameter N = 5;
parameter B = 10;
localparam B_SUM = B+$clog2(N);

input clk;
input i_dval;
input [B-1:0] i_data [N];
output logic         o_dval;
output logic [B-1:0] o_data;

logic [B_SUM-1:0] summed;

always @* begin
	summed = 0;
	for (int i = 0; i < N; i++) begin
		summed += i_data[i];
	end
end

always @(posedge clk) begin
	o_data <= summed/N;
	o_dval <= i_dval;
end

// initial begin
// 	$fsdbDumpfile("mean_sv.fsdb");
// 	$fsdbDumpvars(0, mean_sv, "+mda");
// end

endmodule
