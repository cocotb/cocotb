import logging

import cocotb
from cocotb.triggers import Timer, Lock
from cocotb.result import TestError, TestFailure
from cocotb.utils import get_sim_time

@cocotb.coroutine
def acquire_sem(sem, num_keys, expected_ts, tlog):
    yield sem.acquire(key_count=num_keys)
    tlog.info("Acquired semaphore. key_count=%d", sem.key_count_available)
    ts = get_sim_time()
    if expected_ts != ts:
        raise TestFailure("Expected to acquire semaphore at %d, but acquired at %d" % (expected_ts, ts))


@cocotb.coroutine
def release_sem(sem, key_count, tlog):
    for i in range(key_count):
        yield Timer(2)
        tlog.info("Releasing semaphore. key_count=%d", sem.key_count_available + 1)
        sem.release(1)


@cocotb.test()
def test_lock(dut):
    """
    Test the legacy behavior of the Lock class.
    """
    tlog = logging.getLogger("cocotb.test")
    start_ts = get_sim_time()

    # lock request to timestamp
    # Relative to start_ts
    expected_timestamp = { 0 : 0, # Should not block as there is 1 initial key
                           1 : 2, # Need to wait for 1 key to be returned
                           2 : 4} # Need to wait for 1 key to be returned

    sem = Lock("test_semaphore")

    forks = [cocotb.fork(acquire_sem(sem, 1, expected_timestamp[i]+start_ts, tlog)) for i in range(3)]

    cocotb.fork(release_sem(sem, 2, tlog))

    for fork in forks:
        yield fork.join()


@cocotb.test()
def test_multiple_key_count(dut):
    """
    - Create a semaphore with key_count=5.
    - Make 3 acquire requests each requesting 3 keys.
    - Release 1 key every other timestamp.
    - Predict when the requests are granted.
    """
    tlog = logging.getLogger("cocotb.test")
    start_ts = get_sim_time()

    # lock request to timestamp
    # Relative to start_ts
    expected_timestamp = { 0 : 0, # Should not block as there are 5 initial keys
                           1 : 2, # Need to wait for 1 key to be returned
                           2 : 8} # Need to wait for 3 more keys
    
    sem = Lock("test_semaphore", key_count=5)

    forks = [cocotb.fork(acquire_sem(sem, 3, expected_timestamp[i]+start_ts, tlog)) for i in range(3)]

    cocotb.fork(release_sem(sem, 9, tlog))

    for fork in forks:
        yield fork.join()
