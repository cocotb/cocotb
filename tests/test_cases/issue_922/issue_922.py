import cocotb
from cocotb.triggers import Timer, NullTrigger

class TestException(Exception): pass

@cocotb.coroutine
def a_coroutine_that_fails_soon():
    yield Timer(10, 'ns')
    raise TestException

@cocotb.coroutine
def longer_than_soon():
    yield Timer(100, 'ns')

@cocotb.test()
def runs(dut):
    task = cocotb.run(a_coroutine_that_fails_soon())
    yield longer_than_soon()
    try:
        yield task
    except TestException as e:
        pass  # we never get as far as here right now, but I think we ought to
    else:
        assert False

@cocotb.test(expect_error=True)
def forks(dut):
    task = cocotb.fork(a_coroutine_that_fails_soon())
    yield longer_than_soon()
    assert False
