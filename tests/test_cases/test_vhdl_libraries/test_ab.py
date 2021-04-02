import cocotb


@cocotb.test()
async def test(dut):
    # Toggling an input should trigger the simulator to print a message
    # similar to:
    #
    #   b.vhdl:9:5:@0ms:(report note): :a(structural):b@b(structural):
    #
    dut.x <= False
