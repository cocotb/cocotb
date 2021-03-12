entity b is
  port ( x : in boolean );
end;


architecture structural of b is
begin
  process(x) begin
    report b'instance_name;
  end process;
end;
