import cocotb
from cocotb.clock import Clock
from cocotb_bus.drivers import BusDriver
from cocotb_bus.monitors import BusMonitor
from cocotb.triggers import RisingEdge


class TestDriver(BusDriver):
    _signals = ["data", "valid"]

    def __init__(self, entity, name, clock, **kwargs):
        BusDriver.__init__(self, entity, name, clock, **kwargs)
        self.bus.valid <= 0

    async def _driver_send(self, transaction, sync=True):
        clkedge = RisingEdge(self.clock)
        if sync:
            await clkedge

        self.log.info("Sending {}".format(transaction))
        self.bus.valid <= 1
        self.bus.data <= transaction

        await clkedge
        self.bus.valid <= 0


class TestMonitor(BusMonitor):

    _signals = ["data", "valid"]

    def __init__(self, entity, name, clock, bank=0, **kwargs):
        BusMonitor.__init__(self, entity, name, clock, **kwargs)
        self.bank = bank
        self.add_callback(self._get_result)
        self.expected = []

    async def _monitor_recv(self):
        clkedge = RisingEdge(self.clock)
        while True:
            await clkedge
            if self.bus.valid.value:
                self._recv(int(self.bus.data))

    def _get_result(self, transaction):
        self.log.info("Received {} on bank {}".format(transaction, self.bank))
        exp = self.expected.pop(0)
        assert exp == int(transaction)

    def add_expected(self, transaction):
        self.expected.append(int(transaction))


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith('ghdl') else ())
async def test_array_buses(dut):
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.fork(clock.start())
    clkedge = RisingEdge(dut.clk)
    in_data_0 = TestDriver(dut, "in", dut.clk, array_idx=0)
    in_data_1 = TestDriver(dut, "in", dut.clk, array_idx=1)
    out_data_0 = TestMonitor(dut, "in", dut.clk, array_idx=0, bank=0)
    out_data_1 = TestMonitor(dut, "in", dut.clk, array_idx=1, bank=1)
    out_data_0.add_expected(10)
    out_data_0.add_expected(30)
    out_data_1.add_expected(20)
    out_data_1.add_expected(40)

    await in_data_0.send(10)
    await clkedge
    await in_data_1.send(20)
    await clkedge
    await in_data_0.send(30)
    await clkedge
    await in_data_1.send(40)
    await clkedge
    await clkedge

    assert not out_data_0.expected
    assert not out_data_1.expected
