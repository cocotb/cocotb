import cocotb
from cocotb import triggers, outcomes


@cocotb.coroutine
async def clock(clock_signal):
    while True:
        try:
            clock_signal <= 0
            await triggers.Timer(1, units='ns')
            clock_signal <= 1
            await triggers.Timer(1, units='ns')
        except outcomes.KilledError:
            pass


@cocotb.coroutine
async def killable(dut, state):
    state['killed'] = True
    state['cleanup'] = False
    try:
        await triggers.RisingEdge(dut.clk)
        await triggers.RisingEdge(dut.clk)
        # We expect this coroutine to get killed before the second clock edge.
        state['killed'] = False
    finally:
        # We expect this to run after the coroutine is killed.
        state['cleanup'] = True


@cocotb.coroutine
async def unkillable(dut):
    while True:
        try:
            await triggers.RisingEdge(dut.clk)
        except outcomes.KilledError:
            pass

@cocotb.coroutine
async def killer(dut, killable_task):
    await triggers.RisingEdge(dut.clk)
    killable_task.kill()


@cocotb.coroutine
async def allow_kill(coro):
    try:
        await coro
    except outcomes.KilledError:
        pass

@cocotb.test()
async def test(dut):
    cocotb.fork(clock(dut.clk))
    cocotb.fork(unkillable(dut))
    state = {}
    pB = killable(dut, state)
    pA = killer(dut, pB)
    cocotb.fork(pA)
    cocotb.fork(allow_kill(pB))
    for i in range(3):
        await triggers.RisingEdge(dut.clk)
    assert state['killed']
    assert state['cleanup']
