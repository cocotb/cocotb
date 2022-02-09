# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests relating to cocotb.queue.Queue, cocotb.queue.LifoQueue, cocotb.queue.PriorityQueue
"""
import pytest

import cocotb
from cocotb.queue import LifoQueue, PriorityQueue, Queue, QueueEmpty, QueueFull
from cocotb.regression import TestFactory
from cocotb.triggers import Combine, NullTrigger


async def run_queue_nonblocking_test(dut, queue_type):
    QUEUE_SIZE = 10

    q = queue_type(maxsize=QUEUE_SIZE)

    # queue empty
    assert q.maxsize == QUEUE_SIZE
    assert q.qsize() == 0
    assert q.empty()
    assert not q.full()

    # put one item
    q.put_nowait(0)

    assert q.qsize() == 1
    assert not q.empty()
    assert not q.full()

    # fill queue
    if queue_type is PriorityQueue:
        for k in range(QUEUE_SIZE - 1, 0, -1):
            q.put_nowait(k)
    else:
        for k in range(1, QUEUE_SIZE):
            q.put_nowait(k)

    assert q.qsize() == QUEUE_SIZE
    assert not q.empty()
    assert q.full()

    # overflow
    with pytest.raises(QueueFull):
        q.put_nowait(100)

    # check queue contents
    if queue_type is LifoQueue:
        for k in range(QUEUE_SIZE - 1, -1, -1):
            assert q.get_nowait() == k
    else:
        for k in range(QUEUE_SIZE):
            assert q.get_nowait() == k

    assert q.qsize() == 0
    assert q.empty()
    assert not q.full()

    # underflow
    with pytest.raises(QueueEmpty):
        q.get_nowait()


factory = TestFactory(run_queue_nonblocking_test)
factory.add_option("queue_type", [Queue, PriorityQueue, LifoQueue])
factory.generate_tests()


@cocotb.test()
async def test_queue_contention(dut):
    NUM_PUTTERS = 20
    QUEUE_SIZE = 10

    q = Queue(maxsize=QUEUE_SIZE)

    async def putter(lst, item):
        await q.put(item)
        lst.append(item)

    async def getter(lst, item):
        assert item == await q.get()
        lst.append(item)

    coro_list = []
    putter_list = []
    getter_list = []

    # test put contention
    for k in range(NUM_PUTTERS):
        coro_list.append(await cocotb.start(putter(putter_list, k)))

    assert q.qsize() == QUEUE_SIZE

    # test killed putter
    coro = cocotb.start_soon(putter(putter_list, 100))
    coro.kill()
    coro_list.append(cocotb.start_soon(putter(putter_list, 101)))

    for k in range(NUM_PUTTERS):
        coro_list.append(cocotb.start_soon(getter(getter_list, k)))

    coro_list.append(cocotb.start_soon(getter(getter_list, 101)))

    await Combine(*coro_list)

    assert putter_list == list(range(NUM_PUTTERS)) + [101]
    assert getter_list == list(range(NUM_PUTTERS)) + [101]

    assert q.qsize() == 0

    coro_list = []
    putter_list = []
    getter_list = []

    # test get contention
    for k in range(NUM_PUTTERS):
        coro_list.append(cocotb.start_soon(getter(getter_list, k)))

    # test killed getter
    coro2 = cocotb.start_soon(getter(getter_list, 100))
    coro2.kill()
    coro_list.append(cocotb.start_soon(getter(getter_list, 101)))

    for k in range(NUM_PUTTERS):
        coro_list.append(cocotb.start_soon(putter(putter_list, k)))

    coro_list.append(cocotb.start_soon(putter(putter_list, 101)))

    await Combine(*coro_list)

    assert putter_list == list(range(NUM_PUTTERS)) + [101]
    assert getter_list == list(range(NUM_PUTTERS)) + [101]

    assert q.qsize() == 0


@cocotb.test()
async def test_fair_scheduling(dut):
    NUM_PUTTERS = 10
    NUM_PUTS = 10

    q = Queue(maxsize=1)

    async def putter(i):
        for _ in range(NUM_PUTS):
            await q.put(i)

    # fill queue to force contention
    q.put_nowait(None)

    # create NUM_PUTTER contending putters
    putters = [await cocotb.start(putter(i)) for i in range(NUM_PUTTERS)]

    # remove value that forced contention
    assert q.get_nowait() is None, "Popped unexpected value"

    # test fair scheduling by ensuring that each putter is serviced for its first
    # write before the second write on any putter is serviced.
    for _ in range(NUM_PUTS):
        remaining = set(range(NUM_PUTTERS))
        for _ in range(NUM_PUTTERS):
            v = await q.get()
            assert v in remaining, "Unfair scheduling occurred"
            remaining.remove(v)

    assert all(not p for p in putters), "Not all putters finished?"


async def run_queue_blocking_test(dut, queue_type):
    NUM_PUTTERS = 20
    QUEUE_SIZE = 10

    q = queue_type(maxsize=QUEUE_SIZE)
    ref_q = queue_type()

    async def putter(lst, item):
        await q.put(item)
        ref_q.put_nowait(item)
        lst.append(item)

    async def getter(lst, num):
        item = await q.get()
        assert ref_q.get_nowait() == item
        lst.append(num)

    coro_list = []
    putter_list = []
    getter_list = []

    # test put contention
    for k in range(NUM_PUTTERS):
        coro_list.append(await cocotb.start(putter(putter_list, k)))

    assert q.qsize() == QUEUE_SIZE

    for k in range(NUM_PUTTERS):
        coro_list.append(await cocotb.start(getter(getter_list, k)))

    await Combine(*coro_list)

    assert putter_list == list(range(NUM_PUTTERS))
    assert getter_list == list(range(NUM_PUTTERS))

    assert q.qsize() == 0
    assert ref_q.qsize() == 0

    coro_list = []
    putter_list = []
    getter_list = []

    # test get contention
    for k in range(NUM_PUTTERS):
        coro_list.append(await cocotb.start(getter(getter_list, k)))

    for k in range(NUM_PUTTERS):
        coro_list.append(await cocotb.start(putter(putter_list, k)))

    await Combine(*coro_list)

    assert putter_list == list(range(NUM_PUTTERS))
    assert getter_list == list(range(NUM_PUTTERS))

    assert q.qsize() == 0
    assert ref_q.qsize() == 0


factory = TestFactory(run_queue_blocking_test)
factory.add_option("queue_type", [Queue, PriorityQueue, LifoQueue])
factory.generate_tests()


@cocotb.test()
async def test_str_and_repr(_):
    q = Queue[int](maxsize=1)

    q.put_nowait(0)
    putter = await cocotb.start(q.put(1))

    s = repr(q)
    assert "maxsize" in s
    assert "_queue" in s
    assert "_putters" in s
    assert str(q)[:-1] in s

    assert q.get_nowait() == 0
    # There's now room in the queue and putter has been signalled to wake up
    await NullTrigger()

    # putter has put into queue
    s = repr(q)
    assert "_queue" in s
    assert "_putters" not in s

    assert q.get_nowait() == 1
    getter = await cocotb.start(q.get())

    s = repr(q)
    assert "_putters" not in s
    assert "_getters" in s
    assert str(q)[:-1] in s

    cocotb.start_soon(q.put(2))

    await getter

    s = repr(q)
    assert "_getters" not in s
    assert str(q)[:-1] in s
