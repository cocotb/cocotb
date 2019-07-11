library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity logic_testbench is
    port (
        clk     : in std_logic;
        reset   : in std_logic
    );
end entity logic_testbench;

architecture rtl of logic_testbench is
    -- Normal counters
    signal unsigned_counter_little : unsigned(15 downto 0);
    signal signed_counter_little : signed(16 downto 0);
    signal unsigned_counter_big : unsigned(0 to 15);
    signal signed_counter_big : signed(0 to 16);
    -- Overflowing counters
    signal unsigned_overflow_counter_little : unsigned(2 downto 0);
    signal signed_overflow_counter_little : signed(3 downto 0);
    signal unsigned_overflow_counter_big : unsigned(0 to 2);
    signal signed_overflow_counter_big : signed(0 to 3);
    -- Truncation
    signal truncate_unsigned_little : unsigned(8 downto 0);
    signal truncate_signed_little : signed(9 downto 0);
    signal truncate_unsigned_big : unsigned(0 to 8);
    signal truncate_signed_big : signed(0 to 9);
    -- Extension
    signal extend_unsigned_little : unsigned(8 downto 0);
    signal extend_signed_little : signed(8 downto 0);
    signal extend_unsigned_big : unsigned(0 to 8);
    signal extend_signed_big : signed(0 to 8);
    -- Endian-ness swap
    signal unsigned_counter_little_to_big : unsigned(0 to 15);
    signal signed_counter_little_to_big : signed(0 to 16);
    signal unsigned_counter_big_to_little : unsigned(15 downto 0);
    signal signed_counter_big_to_little : signed(16 downto 0);
    -- Assign integer
    signal unsigned_assigned_signed_little : unsigned(7 downto 0);
    signal signed_assigned_signed_little : signed(8 downto 0);
    signal unsigned_assigned_signed_big : unsigned(0 to 7);
    signal signed_assigned_signed_big : signed(0 to 8);
begin
    normal_count : process (clk, reset)
    begin
        if (reset = '0') then
            unsigned_counter_little <= (others => '0');
            signed_counter_little <= (others => '0');
            unsigned_counter_big <= (others => '0');
            signed_counter_big <= (others => '0');
        elsif (clk'event and clk = '1') then
            unsigned_counter_little <= unsigned_counter_little + 1;
            signed_counter_little <= signed_counter_little + 1;
            unsigned_counter_big <= unsigned_counter_big + 1;
            signed_counter_big <= signed_counter_big + 1;
        end if;
    end process;

    overflow_count : process (clk, reset)
    begin
        if (reset = '0') then
            unsigned_overflow_counter_little <= (others => '0');
            signed_overflow_counter_little <= (others => '0');
            unsigned_overflow_counter_big <= (others => '0');
            signed_overflow_counter_big <= (others => '0');
        elsif (clk'event and clk = '1') then
            unsigned_overflow_counter_little <= unsigned_overflow_counter_little + 1;
            signed_overflow_counter_little <= signed_overflow_counter_little + 1;
            unsigned_overflow_counter_big <= unsigned_overflow_counter_big + 1;
            signed_overflow_counter_big <= signed_overflow_counter_big + 1;
        end if;
    end process;

    -- Truncation
    -- Have to be specified on what you what to truncate, so can always truncate correctly
    truncate_unsigned_little <= unsigned_counter_little(truncate_unsigned_little'range);
    truncate_signed_little <= signed_counter_little(truncate_signed_little'range);
    truncate_unsigned_big <= unsigned_counter_big(truncate_unsigned_big'range);
    truncate_signed_big <= signed_counter_big(truncate_signed_big'range);

    -- Extension
    extension : process (unsigned_overflow_counter_little,
                         signed_overflow_counter_little,
                         unsigned_overflow_counter_big,
                         signed_overflow_counter_big)
    begin
        -- Have to explicitly say how you're extending in VHDL
        extend_unsigned_little <= resize(unsigned_overflow_counter_little, extend_unsigned_little'length);
        extend_signed_little <= resize(signed_overflow_counter_little, extend_signed_little'length);
        -- The 'resize' function explicitly says it extends to the left
        -- Going to treat this like the verilog case where you could assume (incorrectly) it extend the MS-end
        extend_unsigned_big <= resize(unsigned_overflow_counter_big, extend_unsigned_big'length);
        extend_signed_big <= resize(signed_overflow_counter_big, extend_signed_big'length);
    end process;

    -- Endian-ness swap
    unsigned_counter_little_to_big <= unsigned_counter_little;
    signed_counter_little_to_big <= signed_counter_little;
    unsigned_counter_big_to_little <= unsigned_counter_big;
    signed_counter_big_to_little <= signed_counter_big;

    -- Assign an integer
    -- VHDL is great and doesn't let us assign a signed value to an unsigned vector
    --unsigned_assigned_signed_little <= to_unsigned(-57, 8);
    signed_assigned_signed_little <= to_signed(-57, 9);
    --unsigned_assigned_signed_big <= to_unsigned(-57, 8);
    signed_assigned_signed_big <= to_signed(-57, 9);
end rtl;
