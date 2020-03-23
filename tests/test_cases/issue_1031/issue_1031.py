from cocotb import test, fork
from cocotb.triggers import Lock, Timer

@test()
async def test_trigger_lock(dut):

    resource = [0]
    lock = Lock()

    fork(co(resource, lock))
    async with lock:
        for i in range(4):
            resource[0] += 1
            await Timer(10, "ns")
    assert resource[0]==4
    async with lock:
        assert resource[0]==8

async def co(resource, lock):
    await Timer(10, "ns")
    async with lock:
        for i in range(4):
            resource[0] += 1
            await Timer(10, "ns")