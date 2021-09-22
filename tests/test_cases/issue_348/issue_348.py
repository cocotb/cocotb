import cocotb
from cocotb.log import SimLog
from cocotb.triggers import Timer, Edge, RisingEdge, FallingEdge


async def clock_gen(signal, num):
    for x in range(num):
        signal.value = 0
        await Timer(5, 'ns')
        signal.value = 1
        await Timer(5, 'ns')


async def signal_mon(signal, idx, edge):
    _ = SimLog("cocotb.signal_mon.%d.%s" % (idx, signal._name))
    _ = signal.value
    edges = 0

    while True:
        await edge(signal)
        edges += 1

    return edges


class DualMonitor:
    def __init__(self, edge, signal):
        self.log = SimLog(f"cocotb.{edge}.{signal._path}")
        self.edge_type = edge
        self.monitor_edges = [0, 0]
        self.signal = signal

    async def signal_mon(self, signal, idx, edge):
        while True:
            await edge(signal)
            self.monitor_edges[idx] += 1

    async def start(self):
        clock_edges = 10

        cocotb.start_soon(clock_gen(self.signal, clock_edges))
        _ = cocotb.start_soon(self.signal_mon(self.signal, 0, self.edge_type))
        _ = cocotb.start_soon(self.signal_mon(self.signal, 1, self.edge_type))

        await Timer(100, 'ns')

        for mon in self.monitor_edges:
            assert mon, "Monitor saw nothing"


# Cadence simulators: "Unable set up RisingEdge(ModifiableObject(sample_module.clk)) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def issue_348_rising(dut):
    """ Start two monitors on RisingEdge """
    await DualMonitor(RisingEdge, dut.clk).start()


# Cadence simulators: "Unable set up FallingEdge(ModifiableObject(sample_module.clk)) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def issue_348_falling(dut):
    """ Start two monitors on FallingEdge """
    await DualMonitor(FallingEdge, dut.clk).start()


# Cadence simulators: "Unable set up Edge(ModifiableObject(sample_module.clk)) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def issue_348_either(dut):
    """ Start two monitors on Edge """
    await DualMonitor(Edge, dut.clk).start()
