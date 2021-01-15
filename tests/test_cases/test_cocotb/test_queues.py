# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests relating to cocotb.queue.Queue, cocotb.queue.LifoQueue, cocotb.queue.PriorityQueue
"""
import cocotb
from cocotb.queue import Queue, PriorityQueue, LifoQueue, QueueFull, QueueEmpty
from cocotb.regression import TestFactory
from cocotb.triggers import Combine, Timer


async def run_queue_nonblocking_test(dut, queue_type):
    QUEUE_SIZE=10

    q = queue_type(maxsize=QUEUE_SIZE)

    # queue empty
    assert q.maxsize == QUEUE_SIZE
    assert q.qsize() == 0
    assert q.empty()
    assert not q.full()

    assert str(q) == '<{} maxsize={}>'.format(type(q).__name__, q.maxsize)
    assert isinstance(repr(q), str)

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
    got_exception = False
    try:
        q.put_nowait(100)
    except QueueFull:
        got_exception = True
    assert got_exception

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
    got_exception = False
    try:
        q.get_nowait()
    except QueueEmpty:
        got_exception = True
    assert got_exception

    # task counts
    assert q._unfinished_tasks == QUEUE_SIZE

    for k in range(QUEUE_SIZE):
        q.task_done()

    assert q._unfinished_tasks == 0

    got_exception = False
    try:
        q.task_done()
    except ValueError:
        got_exception = True
    assert got_exception


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
        q.task_done()

    cr_list = []
    putter_list = []
    getter_list = []

    # test put contention
    for k in range(NUM_PUTTERS):
        cr_list.append(cocotb.fork(putter(putter_list, k)))

    assert q.qsize() == QUEUE_SIZE

    # test killed putter
    cr = cocotb.fork(putter(putter_list, 100))
    cr.kill()
    cr_list.append(cocotb.fork(putter(putter_list, 101)))

    for k in range(NUM_PUTTERS):
        cr_list.append(cocotb.fork(getter(getter_list, k)))

    cr_list.append(cocotb.fork(getter(getter_list, 101)))

    await Combine(*cr_list)

    assert putter_list == list(range(NUM_PUTTERS))+[101]
    assert getter_list == list(range(NUM_PUTTERS))+[101]

    assert q.qsize() == 0

    cr_list = []
    putter_list = []
    getter_list = []

    # test get contention
    for k in range(NUM_PUTTERS):
        cr_list.append(cocotb.fork(getter(getter_list, k)))

    # test killed getter
    cr2 = cocotb.fork(getter(getter_list, 100))
    cr2.kill()
    cr_list.append(cocotb.fork(getter(getter_list, 101)))

    for k in range(NUM_PUTTERS):
        cr_list.append(cocotb.fork(putter(putter_list, k)))

    cr_list.append(cocotb.fork(putter(putter_list, 101)))

    await Combine(*cr_list)

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

    # test fair scheduling by ensuring that each putter is serviced for it's first
    # write before the second write on any putter is serviced.
    for _ in range(NUM_PUTS):
        remaining = set(range(NUM_PUTTERS))
        for _ in range(NUM_PUTTERS):
            v = await q.get()
            assert v in remaining, "Unfair scheduling occured"
            remaining.remove(v)

    assert all(not p for p in putters), "Not all putters finished?"


@cocotb.test()
async def test_tasks(dut):
    q = Queue()

    for k in range(10):
        q.put_nowait(k)

    assert q._unfinished_tasks == 10

    async def getter():
        while True:
            item = await q.get()
            await Timer(10, 'ns')
            q.task_done()

    cocotb.fork(getter())

    await q.join()

    assert q._unfinished_tasks == 0


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
        q.task_done()

    cr_list = []
    putter_list = []
    getter_list = []

    # test put contention
    for k in range(NUM_PUTTERS):
        cr_list.append(cocotb.fork(putter(putter_list, k)))

    assert q.qsize() == QUEUE_SIZE

    for k in range(NUM_PUTTERS):
        cr_list.append(cocotb.fork(getter(getter_list, k)))

    await Combine(*cr_list)

    assert putter_list == list(range(NUM_PUTTERS))
    assert getter_list == list(range(NUM_PUTTERS))

    assert q.qsize() == 0
    assert ref_q.qsize() == 0

    cr_list = []
    putter_list = []
    getter_list = []

    # test get contention
    for k in range(NUM_PUTTERS):
        cr_list.append(cocotb.fork(getter(getter_list, k)))

    for k in range(NUM_PUTTERS):
        cr_list.append(cocotb.fork(putter(putter_list, k)))

    await Combine(*cr_list)

    assert putter_list == list(range(NUM_PUTTERS))
    assert getter_list == list(range(NUM_PUTTERS))

    assert q.qsize() == 0
    assert ref_q.qsize() == 0


factory = TestFactory(run_queue_blocking_test)
factory.add_option("queue_type", [Queue, PriorityQueue, LifoQueue])
factory.generate_tests()
