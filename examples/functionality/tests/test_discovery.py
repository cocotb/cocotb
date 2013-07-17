
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
def discover_module_values(dut):
    """Discover everything in the dut"""
    yield Timer(0)
    for thing in dut:
        thing.log.info("Found something: %s" % thing.fullname)

@cocotb.test(expect_fail=True)
def discover_value_not_in_dut(dut):
    """Try and get a value from the DUT that is not there"""
    yield Timer(0)
    fake_signal = dut.fake_signal
    yield Timer(0)


@cocotb.test()
def access_single_bit(dut):
    """Access a single bit in a vector of the dut"""
    # FIXME this test fails on Icarus but works on VCS
    dut.stream_in_data <= 0
    yield Timer(10)
    dut.log.info("%s = %d bits" % (str(dut.stream_in_data), len(dut.stream_in_data)))
    dut.stream_in_data[2] <= 1
    yield Timer(10)
    if dut.stream_out_data_comb.value.value != (1<<2):
        raise TestError("%s.%s != %d" %
                (str(dut.stream_out_data_comb),
                dut.stream_out_data_comb.value.value, (1<<2)))



@cocotb.test(expect_fail=True)
def access_single_bit_erroneous(dut):
    """Access a non-existent single bit"""
    yield Timer(10)
    dut.log.info("%s = %d bits" % (str(dut.stream_in_data), len(dut.stream_in_data)))
    bit = len(dut.stream_in_data) + 4
    dut.stream_in_data[bit] <= 1
    yield Timer(10)
