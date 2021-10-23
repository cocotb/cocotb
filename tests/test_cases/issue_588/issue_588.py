# Test case for issue 588- yielding both coroutines and triggers in a list.
# This is a very simple test; it just makes sure we can yield a list of both.

import cocotb
from cocotb import triggers, utils


async def sample_coroutine(dut):
    """ Very simple coroutine that waits 5 ns."""
    await triggers.Timer(5, "ns")
    dut._log.info("Sample coroutine yielded.")


@cocotb.test()
async def issue_588_coroutine_list(dut):
    """ Yield a list of triggers and coroutines."""

    # Record simulation time.
    current_time = utils.get_sim_time("ns")

    # Yield a list, containing a RisingEdge trigger and a coroutine.
    coro = cocotb.start_soon(sample_coroutine(dut))
    await triggers.First(coro, triggers.Timer(100, "ns"))
    coro.kill()

    # Make sure that only 5 ns passed, because the sample coroutine
    # terminated first.
    new_time = utils.get_sim_time("ns")
    assert int(new_time - current_time) == 5, "Did not yield coroutine in list."
