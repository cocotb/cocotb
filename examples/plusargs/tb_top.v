module tb_top ;

    reg [1000:0] foo_string;
    integer result;

initial begin
    $display("Plusargs test");
    result = $value$plusargs("foo=%s", foo_string);	
    $display("Plusarg foo has value %0s", foo_string);

end
endmodule //: tb_top
