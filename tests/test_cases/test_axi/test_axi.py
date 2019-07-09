""" Copyright 2019 by Ben Coughlan <ben@liquidinstruments.com>

Licensed under Revised BSD License
All rights reserved. See LICENSE.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.drivers.amba import AXI4MemoryMap
from cocotb.drivers.amba import handshake
from cocotb.result import ReturnValue
from cocotb.bus import Bus
from cocotb.monitors.amba import AXI4
from cocotb.scoreboard import Scoreboard

CLK_PERIOD = 10


@cocotb.coroutine
def write(clock, bus, addr, data, thread_id=0, burst_type=1):
    if not isinstance(data, (list, tuple)):
        data = [data]

    bus.awid <= thread_id
    bus.awaddr <= addr
    bus.awlen <= len(data) - 1  # TODO unaligned transfers
    bus.awsize <= 0x03  # 64 bit
    bus.awburst <= burst_type
    bus.awlock <= 0x00
    bus.awcache <= 0x00
    bus.awprot <= 0x00
    bus.awqos <= 0x00

    aw = cocotb.fork(handshake(clock, bus.awvalid, bus.awready))

    @cocotb.coroutine
    def _write_thread(clock, bus, data):
        for i, d in enumerate(data):
            bus.wdata <= d
            bus.wstrb <= 0xFF
            bus.wlast <= (1 if i == len(data)-1 else 0)
            yield handshake(clock, bus.wvalid, bus.wready)
            bus.wlast <= 0
    bus.wid <= thread_id

    w = cocotb.fork(_write_thread(clock, bus, data))

    yield aw.join()
    yield w.join()

    @cocotb.coroutine
    def _wait_for_bresp(clock, bus, wid):
        while True:
            yield handshake(clock, bus.bready, bus.bvalid)
            if int(bus.bid) == int(wid):
                break

    raise ReturnValue(cocotb.fork(_wait_for_bresp(clock, bus, thread_id)))


@cocotb.coroutine
def read(clock, bus, addr, length, thread_id=0, burst_type=1):
    bus.arid <= thread_id
    bus.araddr <= addr
    bus.arlen <= length - 1
    bus.arsize <= 3
    bus.arburst <= burst_type
    bus.arlock <= 0
    bus.arcache <= 0
    bus.arprot <= 0
    bus.arqos <= 0

    ar = cocotb.fork(handshake(clock, bus.arvalid, bus.arready))
    yield ar.join()

    @cocotb.coroutine
    def wait_for_rresp(clock, bus, rid):
        data = []

        while True:
            yield handshake(clock, bus.rready, bus.rvalid)

            if int(bus.rid) == rid:
                data.append(int(bus.rdata))
                if int(bus.rlast):
                    break

    raise ReturnValue(cocotb.fork(wait_for_rresp(clock, bus, thread_id)))


def get_bus(dut):
    signals = [
        'awid', 'awaddr', 'awlen', 'awsize', 'awburst', 'awlock', 'awcache',
        'awprot', 'awqos', 'awvalid', 'awready',
        'wid', 'wdata', 'wstrb', 'wlast', 'wvalid', 'wready',
        'bid', 'bresp', 'bvalid', 'bready',
        'arid', 'araddr', 'arlen', 'arsize', 'arburst', 'arvalid', 'arready',
        'arlock', 'arcache', 'arprot', 'arqos',
        'rid', 'rdata', 'rresp', 'rlast', 'rvalid', 'rready']

    saxi_bus = Bus(dut, "SAXI", signals)
    saxi_bus.awvalid <= 0
    saxi_bus.wvalid <= 0
    saxi_bus.bready <= 0
    saxi_bus.wlast <= 0
    saxi_bus.arvalid <= 0
    saxi_bus.rready <= 0
    return saxi_bus


@cocotb.coroutine
def reset(dut):
    dut.Reset <= 1
    cocotb.fork(Clock(dut.Clk, CLK_PERIOD, units='ns').start())
    yield ClockCycles(dut.Clk, 3)
    dut.Reset <= 0
    yield ClockCycles(dut.Clk, 3)


@cocotb.test()
def test_handshake(dut):
    """Test the timing of handshake

    Just twiddles the handshake lines on AR
    """
    dut.SAXI_arready <= 0
    dut.SAXI_araddr <= 0
    dut.SAXI_arvalid <= 0
    yield reset(dut)

    mon = AXI4(dut, "MAXI", dut.Clk, reset=dut.Reset)
    sb = Scoreboard(dut, fail_immediately=False)
    sb.add_interface(mon, [
        ('araddr', 0x01),
        ('araddr', 0x02),
        ('araddr', 0x03),
        ('araddr', 0x04),
        ('araddr', 0x05),
        ('araddr', 0x06),
        ('araddr', 0x07), ('araddr', 0x07), ('araddr', 0x07),
        ('araddr', 0x08), ('araddr', 0x08), ('araddr', 0x08),
        ('araddr', 0x09), ('araddr', 0x09), ('araddr', 0x09),
        ('araddr', 0x0A), ('araddr', 0x0A), ('araddr', 0x0A),
    ])

    @cocotb.coroutine
    def _test(dut, data, delay, loop_delay, loops):
        dut.SAXI_araddr <= data
        dut.SAXI_arvalid <= 0

        for i in range(loops):
            t = cocotb.fork(
                handshake(dut.Clk, dut.MAXI_arready,
                          dut.MAXI_arvalid, delay=delay))

            if loop_delay:
                yield ClockCycles(dut.Clk, loop_delay)

            dut.SAXI_arvalid <= 1
            yield t.join()
            dut.SAXI_arvalid <= 0

        yield ClockCycles(dut.Clk, 3)

    yield _test(dut, 0x01, delay=-1, loop_delay=0, loops=1)
    yield _test(dut, 0x02, delay=-1, loop_delay=1, loops=1)
    yield _test(dut, 0x03, delay=-1, loop_delay=3, loops=1)
    yield _test(dut, 0x04,  delay=0, loop_delay=0, loops=1)
    yield _test(dut, 0x05,  delay=0, loop_delay=1, loops=1)
    yield _test(dut, 0x06,  delay=1, loop_delay=0, loops=1)
    yield _test(dut, 0x07,  delay=1, loop_delay=0, loops=3)
    yield _test(dut, 0x08,  delay=0, loop_delay=0, loops=3)
    yield _test(dut, 0x09, delay=-1, loop_delay=0, loops=3)
    yield _test(dut, 0x0A,  delay=3, loop_delay=0, loops=3)

    yield ClockCycles(dut.Clk, 3)


@cocotb.test()
def test_write(dut):
    """Test Master AXI Write
    """
    mon = AXI4(dut, "MAXI", dut.Clk, reset=dut.Reset)
    sb = Scoreboard(dut, fail_immediately=False)
    sb.add_interface(mon, [
        ('awaddr', 0x00), ('wdata', 0xAA), ('bid', 0x00),
        ('awaddr', 0x10), ('wdata', 0xBB), ('bid', 0x01),
        ('awaddr', 0x20), ('wdata', 0xCC), ('bid', 0x02),
        ('awaddr', 0x30), ('wdata', 0xDD), ('wdata', 0xEE), ('wdata', 0xFF),
        ('bid', 0x03),
    ])

    AXI4MemoryMap(1024, dut, "MAXI", dut.Clk, awready_delay=-1,
                  wready_delay=-1, bresp_delay=10, max_threads=1)
    bus = get_bus(dut)

    yield reset(dut)

    a = yield write(dut.Clk, bus, 0x00, [0xAA], thread_id=0x00)
    yield a.join()
    b = yield write(dut.Clk, bus, 0x10, [0xBB], thread_id=0x01)
    yield b.join()
    c = yield write(dut.Clk, bus, 0x20, [0xCC], thread_id=0x02)
    yield c.join()
    d = yield write(dut.Clk, bus, 0x30, [0xDD, 0xEE, 0xFF], thread_id=0x03)
    yield d.join()

    yield ClockCycles(dut.Clk, 3)


@cocotb.test()
def test_write_multithread(dut):
    """Test Master AXI Write multithreaded
    """
    mon = AXI4(dut, "MAXI", dut.Clk, reset=dut.Reset)
    sb = Scoreboard(dut, fail_immediately=False)
    sb.add_interface(mon, [
        ('awaddr', 0x00), ('wdata', 0xAA), ('wdata', 0xAA), ('wdata', 0xAA),
        ('bid', 0x00),
        ('awaddr', 0x10), ('wdata', 0xBB), ('wdata', 0xBB), ('wdata', 0xBB),
        ('bid', 0x01),
        ('awaddr', 0x20), ('wdata', 0xCC), ('wdata', 0xCC), ('wdata', 0xCC),
        ('bid', 0x02),
        ('awaddr', 0x30), ('wdata', 0xDD), ('wdata', 0xEE), ('wdata', 0xFF),
        ('bid', 0x03),
    ], reorder_depth=5)

    AXI4MemoryMap(1024, dut, "MAXI", dut.Clk, awready_delay=-1,
                  wready_delay=-1, bresp_delay=30, max_threads=2)
    bus = get_bus(dut)

    yield reset(dut)

    a = yield write(dut.Clk, bus, 0x00, [0xAA, 0xAA, 0xAA], thread_id=0x00)
    b = yield write(dut.Clk, bus, 0x10, [0xBB, 0xBB, 0xBB], thread_id=0x01)
    c = yield write(dut.Clk, bus, 0x20, [0xCC, 0xCC, 0xCC], thread_id=0x02)
    d = yield write(dut.Clk, bus, 0x30, [0xDD, 0xEE, 0xFF], thread_id=0x03)

    yield a.join()
    yield b.join()
    yield c.join()
    yield d.join()

    yield ClockCycles(dut.Clk, 3)


@cocotb.test()
def test_read(dut):
    """Test Master AXI Read
    """
    mon = AXI4(dut, "MAXI", dut.Clk, reset=dut.Reset)
    sb = Scoreboard(dut, fail_immediately=False)
    sb.add_interface(mon, [
        ('araddr', 0x00), ('rdata', 0x00),
        ('araddr', 0x10), ('rdata', 0x00),
        ('araddr', 0x20), ('rdata', 0x00), ('rdata', 0x00), ('rdata', 0x00),
    ])

    AXI4MemoryMap(1024, dut, "MAXI", dut.Clk, arready_delay=-1,
                  rresp_delay=10, max_threads=1)
    bus = get_bus(dut)

    yield reset(dut)

    a = yield read(dut.Clk, bus, 0x00, 1, thread_id=0x00)
    yield a.join()
    b = yield read(dut.Clk, bus, 0x10, 1, thread_id=0x00)
    yield b.join()
    c = yield read(dut.Clk, bus, 0x20, 3, thread_id=0x00)
    yield c.join()

    yield ClockCycles(dut.Clk, 3)


@cocotb.test()
def test_read_multithread(dut):
    """Test Master AXI Read
    """
    mon = AXI4(dut, "MAXI", dut.Clk, reset=dut.Reset)
    sb = Scoreboard(dut, fail_immediately=False)
    sb.add_interface(mon, [
        ('araddr', 0x00), ('rdata', 0x00), ('rdata', 0x00), ('rdata', 0x00),
        ('araddr', 0x10), ('rdata', 0x00), ('rdata', 0x00), ('rdata', 0x00),
        ('araddr', 0x20), ('rdata', 0x00), ('rdata', 0x00), ('rdata', 0x00),
        ('araddr', 0x30), ('rdata', 0x00), ('rdata', 0x00), ('rdata', 0x00),
    ], reorder_depth=5)

    AXI4MemoryMap(1024, dut, "MAXI", dut.Clk, arready_delay=-1,
                  rresp_delay=10, max_threads=2)
    bus = get_bus(dut)

    yield reset(dut)

    a = yield read(dut.Clk, bus, 0x00, 3, thread_id=0x00)
    b = yield read(dut.Clk, bus, 0x10, 3, thread_id=0x01)
    c = yield read(dut.Clk, bus, 0x20, 3, thread_id=0x02)
    d = yield read(dut.Clk, bus, 0x30, 3, thread_id=0x03)

    yield a.join()
    yield b.join()
    yield c.join()
    yield d.join()

    yield ClockCycles(dut.Clk, 3)


@cocotb.test()
def test_read_write(dut):
    """Test Master AXI Read and Writing
    """
    mon = AXI4(dut, "MAXI", dut.Clk, reset=dut.Reset)
    sb = Scoreboard(dut, fail_immediately=False)
    sb.add_interface(mon, [
        ('awaddr', 0x00), ('wdata', 0xAA), ('bid', 0x00),
        ('araddr', 0x00), ('rdata', 0xAA), ('rdata', 0x00), ('rdata', 0x00),

        ('awaddr', 0x08), ('wdata', 0xBB), ('bid', 0x01),
        ('araddr', 0x00), ('rdata', 0xAA), ('rdata', 0xBB), ('rdata', 0x00),

        ('awaddr', 0x00), ('wdata', 0xCC), ('wdata', 0xCC), ('wdata', 0xCC),
        ('bid', 0x02),
        ('araddr', 0x00), ('rdata', 0xCC), ('rdata', 0xCC), ('rdata', 0xCC),
    ], reorder_depth=5)

    AXI4MemoryMap(1024, dut, "MAXI", dut.Clk, awready_delay=-1,
                  wready_delay=-1, bresp_delay=10, arready_delay=-1,
                  rresp_delay=3, max_threads=1)
    bus = get_bus(dut)

    yield reset(dut)

    a = yield write(dut.Clk, bus, 0x00, [0xAA], thread_id=0x00)
    yield a.join()
    a = yield read(dut.Clk, bus, 0x00, 3, thread_id=0x00)
    yield a.join()

    a = yield write(dut.Clk, bus, 0x08, [0xBB], thread_id=0x01)
    yield a.join()
    a = yield read(dut.Clk, bus, 0x00, 3, thread_id=0x00)
    yield a.join()

    a = yield write(dut.Clk, bus, 0x00, [0xCC, 0xCC, 0xCC], thread_id=0x02)
    yield a.join()
    a = yield read(dut.Clk, bus, 0x00, 3, thread_id=0x00)
    yield a.join()


    yield ClockCycles(dut.Clk, 3)
