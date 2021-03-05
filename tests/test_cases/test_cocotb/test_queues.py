# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests relating to cocotb.queue.Queue, cocotb.queue.LifoQueue, cocotb.queue.PriorityQueue
"""
import cocotb
from cocotb.queue import Queue, PriorityQueue, LifoQueue, QueueFull, QueueEmpty
from cocotb.regression import TestFactory
from cocotb.triggers import Combine, NullTrigger
import pytest


async def run_queue_nonblocking_test(dut, queue_type):
    QUEUE_SIZE=10

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
        for k in range(QUEUE_SIZE-1, 0, -1):
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
        for k in range(QUEUE_SIZE-1, -1, -1):
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
    NUM_PUTTERS=20
    QUEUE_SIZE=10

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
        coro_list.append(cocotb.fork(putter(putter_list, k)))

    assert q.qsize() == QUEUE_SIZE

    # test killed putter
    coro = cocotb.fork(putter(putter_list, 100))
    coro.kill()
    coro_list.append(cocotb.fork(putter(putter_list, 101)))

    for k in range(NUM_PUTTERS):
        coro_list.append(cocotb.fork(getter(getter_list, k)))

    coro_list.append(cocotb.fork(getter(getter_list, 101)))

    await Combine(*coro_list)

    assert putter_list == list(range(NUM_PUTTERS))+[101]
    assert getter_list == list(range(NUM_PUTTERS))+[101]

    assert q.qsize() == 0

    coro_list = []
    putter_list = []
    getter_list = []

    # test get contention
    for k in range(NUM_PUTTERS):
        coro_list.append(cocotb.fork(getter(getter_list, k)))

    # test killed getter
    coro2 = cocotb.fork(getter(getter_list, 100))
    coro2.kill()
    coro_list.append(cocotb.fork(getter(getter_list, 101)))

    for k in range(NUM_PUTTERS):
        coro_list.append(cocotb.fork(putter(putter_list, k)))

    coro_list.append(cocotb.fork(putter(putter_list, 101)))

    await Combine(*coro_list)

    assert putter_list == list(range(NUM_PUTTERS))+[101]
    assert getter_list == list(range(NUM_PUTTERS))+[101]

    assert q.qsize() == 0


@cocotb.test()
async def test_fair_scheduling(dut):
    NUM_PUTTERS=10
    NUM_PUTS=10

    q = Queue(maxsize=1)

    async def putter(i):
        for _ in range(NUM_PUTS):
            await q.put(i)

    # fill queue to force contention
    q.put_nowait(None)

    # create NUM_PUTTER contending putters
    putters = [cocotb.fork(putter(i)) for i in range(NUM_PUTTERS)]

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
    NUM_PUTTERS=20
    QUEUE_SIZE=10

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
        coro_list.append(cocotb.fork(putter(putter_list, k)))

    assert q.qsize() == QUEUE_SIZE

    for k in range(NUM_PUTTERS):
        coro_list.append(cocotb.fork(getter(getter_list, k)))

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
        coro_list.append(cocotb.fork(getter(getter_list, k)))

    for k in range(NUM_PUTTERS):
        coro_list.append(cocotb.fork(putter(putter_list, k)))

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
    putter = cocotb.fork(q.put(1))

    s = repr(q)
    assert "maxsize" in s
    assert "_queue" in s
    assert "_putters" in s
    assert str(q)[:-1] in s

    assert q.get_nowait() == 0
    getter = cocotb.fork(q.get())

    s = repr(q)
    assert "_putters" not in s
    assert "_getters" in s
    assert str(q)[:-1] in s

    await getter

    s = repr(q)
    assert "_getters" not in s
    assert str(q)[:-1] in s


@cocotb.test()
async def test_wait_full(_):
    QUEUE_SIZE = 5

    q = Queue()

    with pytest.raises(RuntimeError):
        await q.wait_full()

    q = Queue(maxsize=QUEUE_SIZE)

    async def full_coro():
        await q.wait_full()

    fwaiter = cocotb.fork(full_coro())
    assert not fwaiter._finished

    for i in range(QUEUE_SIZE - 1):
        q.put_nowait(i)

    assert not q.full()
    assert not fwaiter._finished

    q.put_nowait(QUEUE_SIZE - 1)

    assert q.full()
    assert not fwaiter._finished

    await NullTrigger()

    assert q.full()
    assert fwaiter._finished

    # wait on already full queue
    fwaiter2 = cocotb.fork(full_coro())

    await NullTrigger()

    assert fwaiter2._finished

    q.get_nowait()

    assert not q.full()

    fwaiter = cocotb.fork(full_coro())
    assert not fwaiter._finished


@cocotb.test()
async def test_wait_empty(_):
    QUEUE_SIZE = 5
    q = Queue(maxsize=QUEUE_SIZE)

    # fill queue
    for i in range(QUEUE_SIZE):
        q.put_nowait(i)

    async def empty_coro():
        await q.wait_empty()

    ewaiter = cocotb.fork(empty_coro())
    assert not q.empty()
    assert not ewaiter._finished

    for _ in range(QUEUE_SIZE - 1):
        q.get_nowait()

    assert not q.empty()
    assert not ewaiter._finished

    q.get_nowait()

    assert q.empty()
    assert not ewaiter._finished

    await NullTrigger()

    assert q.empty()
    assert ewaiter._finished

    # wait on already empty queue
    ewaiter2 = cocotb.fork(empty_coro())

    await NullTrigger()

    assert ewaiter2._finished

    q.put_nowait(0)

    assert not q.empty()

    ewaiter = cocotb.fork(empty_coro())
    assert not ewaiter._finished
    ewaiter.kill()
