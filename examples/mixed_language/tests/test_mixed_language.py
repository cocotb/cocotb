import cocotb
from cocotb.triggers import Timer
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock


@cocotb.test()
async def mixed_language_accessing_test(dut):
    """Try accessing handles and setting values in a mixed language environment."""
    await Timer(100, units="ns")

    verilog = dut.i_swapper_sv
    dut._log.info("Got: %s" % repr(verilog._name))

    vhdl = dut.i_swapper_vhdl
    dut._log.info("Got: %s" % repr(vhdl._name))

    verilog.reset_n.value = 1
    await Timer(100, units="ns")

    vhdl.reset_n.value = 1
    await Timer(100, units="ns")

    assert int(verilog.reset_n) == int(vhdl.reset_n), "reset_n signals were different"

    # Try accessing an object other than a port...
    verilog.flush_pipe.value
    vhdl.flush_pipe.value
    
@cocotb.test()
async def mixed_language_functional_test(dut):
    """Try concurrent simulation of VHDL and Verilog and check the output."""
    await Timer(100, units="ns")

    verilog = dut.i_swapper_sv
    dut._log.info("Got: %s" % repr(verilog._name))

    vhdl = dut.i_swapper_vhdl
    dut._log.info("Got: %s" % repr(vhdl._name))

    # setup default valies
    dut.reset_n.value = 0
    dut.stream_out_ready.value = 1

    dut.stream_in_startofpacket.value = 0     
    dut.stream_in_endofpacket.value = 0    
    dut.stream_in_data.value = 0
    dut.stream_in_valid.value = 1
    dut.stream_in_empty.value = 0

    dut.csr_address.value = 0
    dut.csr_read.value = 0
    dut.csr_write.value = 0
    dut.csr_writedata.value = 0

    # reset cycle
    await Timer(100, units="ns")
    dut.reset_n.value = 1
    await Timer(100, units="ns")

    # start clock
    cocotb.start_soon(Clock(dut.clk, 10, units='ns').start())
    await Timer(500, units="ns")

    # transmit some packages
    previouse_indata = 0
    for pkg in range(1,5):
        print("pkg#" + str(pkg))
        for i in range(1,10):  
            await RisingEdge(dut.clk)
            previouse_indata = dut.stream_in_data.value

            ## write stream in data
            dut.stream_in_startofpacket.value = 1 == 1;      
            dut.stream_in_endofpacket.value = 1 == 20;      
            dut.stream_in_data.value = i + 0x81FFFFFF2B00
            dut.stream_in_valid.value = 1
            await RisingEdge(dut.clk)
            dut.stream_in_valid.value = 0

            ## await stream out data 
            await RisingEdge(dut.clk)
            await RisingEdge(dut.clk)

            ## compare in and out data    
            assert int(previouse_indata) == int(dut.stream_out_data.value), "stream in data and stream out data were different"



