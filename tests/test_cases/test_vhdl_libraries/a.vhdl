library blib;

entity a is
  port ( x : in boolean );
end;

architecture structural of a is
begin
  b : entity blib.b port map (x);
end;
