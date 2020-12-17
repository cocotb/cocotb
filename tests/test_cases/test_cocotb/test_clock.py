# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests relating to cocotb.clock.Clock
"""
from contextlib import contextmanager
import re
import warnings

import cocotb
from cocotb.clock import Clock, CClock
from cocotb.result import SimTimeoutError
from cocotb.triggers import Timer, RisingEdge, FallingEdge, First, with_timeout
from cocotb.utils import get_sim_time, get_sim_steps, get_time_from_sim_steps
from math import isclose

from common import assert_raises


@cocotb.test()
async def test_clock_with_units(dut):
    clk_1mhz   = Clock(dut.clk, 1.0, units='us')
    clk_250mhz = Clock(dut.clk, 4.0, units='ns')

    assert str(clk_1mhz) == "Clock(1.0 MHz)"
    dut._log.info('Created clock >{}<'.format(str(clk_1mhz)))

    assert str(clk_250mhz) == "Clock(250.0 MHz)"
    dut._log.info('Created clock >{}<'.format(str(clk_250mhz)))

    clk_gen = cocotb.fork(clk_1mhz.start())

    start_time_ns = get_sim_time(units='ns')

    await Timer(1, "ns")
    await RisingEdge(dut.clk)

    edge_time_ns = get_sim_time(units='ns')
    assert isclose(edge_time_ns, start_time_ns + 1000.0), "Expected a period of 1 us"

    start_time_ns = edge_time_ns

    await RisingEdge(dut.clk)
    edge_time_ns = get_sim_time(units='ns')
    assert isclose(edge_time_ns, start_time_ns + 1000.0), "Expected a period of 1 us"

    clk_gen.kill()

    clk_gen = cocotb.fork(clk_250mhz.start())

    start_time_ns = get_sim_time(units='ns')

    await Timer(1, "ns")
    await RisingEdge(dut.clk)

    edge_time_ns = get_sim_time(units='ns')
    assert isclose(edge_time_ns, start_time_ns + 4.0), "Expected a period of 4 ns"

    start_time_ns = edge_time_ns

    await RisingEdge(dut.clk)
    edge_time_ns = get_sim_time(units='ns')
    assert isclose(edge_time_ns, start_time_ns + 4.0), "Expected a period of 4 ns"

    clk_gen.kill()


@cocotb.test(timeout_time=100, timeout_unit='us')
async def test_external_clock(dut):
    """Test awaiting on an external non-cocotb coroutine decorated function"""
    clk_gen = cocotb.fork(Clock(dut.clk, 100, "ns").start())
    count = 0
    while count != 100:
        await RisingEdge(dut.clk)
        count += 1
    clk_gen.kill()


@cocotb.test(timeout_time=100, timeout_unit='us')
async def test_simulator_clock(dut):
    cclk = CClock(dut.clk, 100, units='ns')
    cclk.start()
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    cclk.stop()
    del cclk

    cclk = CClock.from_period_tuple(dut.clk, (321654, 4858962), units='step')
    cclk.start()
    await RisingEdge(dut.clk)
    start = get_sim_time()
    await FallingEdge(dut.clk)
    toggle = get_sim_time()
    await RisingEdge(dut.clk)
    end = get_sim_time()
    cclk.stop()
    del cclk
    # Test that duty cycle conversion wasn't lossy
    assert toggle - start == 321654, toggle - start
    assert end - toggle == 4858962, end - toggle

    # Test that calling start() on a running CClock doesn't cause error
    cclk = CClock.from_period_tuple(dut.clk, (50, 50), units='ns')
    cclk.start()
    cclk.start()
    assert cclk.is_running is True
    start = get_sim_time(units='ns')
    await FallingEdge(dut.clk)
    await RisingEdge(dut.clk)
    end = get_sim_time(units='ns')
    assert end - start == 100
    cclk.stop()
    del cclk

    cclk = CClock(dut.clk, period=100, units='ns')
    assert cclk.is_running is False
    cclk.start()
    assert cclk.is_running is True
    for _ in range(100):
        await RisingEdge(dut.clk)


@cocotb.test()
async def test_simulator_clock_killed(dut):
    """Test that simulator clock is killed between tests"""
    t = await First(Timer(100, 'us'), RisingEdge(dut.clk))
    assert t is not RisingEdge(dut.clk)
    assert type(t) is Timer


@cocotb.test()
async def test_simulator_clock_jitter(dut):
    """Test clock jitter generation"""
    cclk = CClock(dut.clk, 1000, units='ns', jitter=30)
    cclk.start()

    edge_times = []
    for _ in range(10000):
        await RisingEdge(dut.clk)
        edge_times.append(get_sim_time())
    cclk.stop()

    from itertools import islice

    period_values = []
    jitter_values = []
    for first, last in zip(islice(edge_times, 0, None), islice(edge_times, 1, None)):
        period = last - first
        jitter = period - get_sim_steps(1000, 'ns')
        period_values.append(period)
        jitter_values.append(jitter)

    for period in period_values:
        assert period >= get_sim_steps(970, units='ns'), "{}".format(period)
        assert period <= get_sim_steps(1030, units='ns'), "{}".format(period)

    # Negative 3-sigma to 3-sigma
    jitter_dist = [[] for _ in range(6)]

    for jitter in jitter_values:
        jitter_ns = get_time_from_sim_steps(jitter, 'ns')
        for sigma in range(-3, 3):
            if sigma * 10 <= jitter_ns < (sigma + 1) * 10:
                jitter_dist[sigma].append(jitter_ns)

    dut._log.info("Jitter distribution:")
    for sigma in range(-3, 3):
        dut._log.info("{} sigma: {:>3} ({:.2%})".format(sigma if sigma < 0 else sigma + 1, len(jitter_dist[sigma]), len(jitter_dist[sigma]) / len(jitter_values)))


@cocotb.test()
async def test_simulator_clock_periods(dut):
    """Test clock stopping after set number of periods"""
    cclk = CClock(dut.clk, 100, units='ns')

    # Test keyword-only args
    with assert_raises(TypeError):
        cclk.start(10, posedge_first=True)
    assert cclk.is_running is False

    with assert_raises(ValueError, pattern="Periods value must be a non-negative integer"):
        cclk.start(periods=-2)

    cclk.start(periods=0)
    assert cclk.is_running is False

    cclk.start(periods=None, posedge_first=False)
    assert cclk.is_running is True
    cclk.stop()

    cclk.start(periods=10, posedge_first=False)
    edges = 0

    async def count_edges():
        nonlocal edges
        while True:
            await RisingEdge(dut.clk)
            edges += 1
    coro = cocotb.fork(count_edges())
    t = await First(Timer(10, units='us'), coro)
    assert type(t) == Timer
    assert edges == 10, edges
    assert cclk.is_running is False
    coro.kill()

    cclk.start()
    start = get_sim_time(units='ns')
    await FallingEdge(dut.clk)
    await RisingEdge(dut.clk)
    end = get_sim_time(units='ns')
    assert end - start == 100
    cclk.stop()


@cocotb.test()
async def test_simulator_clock_polarity(dut):
    """Test clock polarity using posedge_first"""
    cclk = CClock(dut.clk, 100, units='ns')

    dut.clk.setimmediatevalue(0)
    await Timer(1, units='step')
    assert dut.clk.value.integer == 0
    assert cclk.is_running is False
    cclk.start(posedge_first=True)
    await Timer(1, units='step')
    assert dut.clk.value.integer == 1
    cclk.stop()

    dut.clk.setimmediatevalue(1)
    await Timer(1, units='step')
    assert dut.clk.value.integer == 1
    assert cclk.is_running is False
    cclk.start(posedge_first=False)
    await Timer(1, units='step')
    assert dut.clk.value.integer == 0
    cclk.stop()

    @cocotb.coroutine   # decorating `async def` is required to use `First`
    async def wait_edge(edge):
        await edge(dut.clk)
        return edge

    # Test edge order when posedge_first=True
    assert cclk.is_running is False
    cclk.start()
    await Timer(1, units='step')
    first_edge = await First(wait_edge(RisingEdge), wait_edge(FallingEdge))
    assert first_edge is FallingEdge
    cclk.stop()

    await Timer(100, units='ns')

    # Test edge order when posedge_first=False
    assert cclk.is_running is False
    cclk.start(posedge_first=False)
    first_edge = await First(wait_edge(RisingEdge), wait_edge(FallingEdge))
    assert first_edge is RisingEdge
    cclk.stop()


# Some simulators don't trigger RisingEdge / FallingEdge for 0-time pulse
@cocotb.test(expect_error=SimTimeoutError if cocotb.SIM_NAME.lower().startswith(("riviera", "aldec", "ghdl")) else ())
async def test_simulator_clock_duty_cycle(dut):
    """Test duty cycle"""

    @cocotb.coroutine  # cocotb.coroutine necessary to use in with_timeout
    async def check_duty_cycle(exp):
        dut._log.info("Testing duty cycle of {}".format(exp))
        await RisingEdge(dut.clk)
        start = get_sim_time()
        await FallingEdge(dut.clk)
        toggle = get_sim_time()
        await RisingEdge(dut.clk)
        end = get_sim_time()

        period = end - start
        high = toggle - start
        duty_cycle = high / period

        # Check duty cycle within 0.1%
        assert abs(exp - duty_cycle) < .001

    cclk = CClock(dut.clk, period=100, units='ns')
    cclk.start()
    await with_timeout(check_duty_cycle(0.5), 1, 'us')
    cclk.stop()
    del cclk

    cclk = CClock(dut.clk, period=100, units='ns', duty_cycle=0.1)
    cclk.start()
    await with_timeout(check_duty_cycle(0.1), 1, 'us')
    cclk.stop()
    del cclk

    cclk = CClock(dut.clk, period=100, units='ns', duty_cycle=0.99)
    cclk.start()
    await with_timeout(check_duty_cycle(0.99), 1, 'us')
    cclk.stop()
    del cclk

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        cclk = CClock(dut.clk, period=100, units='ns', duty_cycle=0)
        cclk.start()
        await with_timeout(check_duty_cycle(0), 1, 'us')
        cclk.stop()
        del cclk

        cclk = CClock(dut.clk, period=100, units='ns', duty_cycle=1)
        cclk.start()
        await with_timeout(check_duty_cycle(1), 1, 'us')
        cclk.stop()
        del cclk


@contextmanager
def assert_warn(warning_category, pattern=None):
    warns = []
    try:
        with warnings.catch_warnings(record=True) as warns:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            yield warns  # note: not a cocotb yield, but a contextlib one!
    finally:
        assert len(warns) >= 1
        msg = "Expected {}".format(warning_category.__qualname__)
        assert issubclass(warns[0].category, warning_category), msg
        if pattern is not None:
            assert re.match(pattern, str(warns[0].message)), \
                "Correct warn type caught, but message did not match pattern"


@cocotb.test()
async def test_simulator_clock_invalid_args(dut):
    """Test invalid arguments and combinations of arguments"""
    with assert_raises(TypeError, pattern=r"Clock period must be a 2-tuple"):
        CClock.from_period_tuple(dut.clk, period=100, units='ns')

    with assert_raises(ValueError, pattern=r"Clock period tuple must have 2 members"):
        CClock.from_period_tuple(dut.clk, period=(100,))

    with assert_raises(ValueError, pattern=r"Clock period tuple must have 2 members"):
        CClock.from_period_tuple(dut.clk, period=(100,100,100))

    with assert_raises(ValueError, pattern=r"Duty cycle must be in range \[0, 1\]"):
        CClock(dut.clk, period=100, duty_cycle=-.0001)

    with assert_raises(ValueError, pattern=r"Duty cycle must be in range \[0, 1\]"):
        CClock(dut.clk, period=100, duty_cycle=100)


@cocotb.test()
async def test_simulator_dot_sim_clock(dut):
    """Test cocotb.simulator.sim_clock"""
    clk = cocotb.simulator.create_clock(dut.clk._handle, 33, 67, high_jitter=2, low_jitter=4)

    with assert_raises(ValueError, pattern=r"Number of clock toggles cannot be negative"):
        clk.start(-1, True)

    with assert_raises(TypeError):
        cocotb.simulator.create_clock("nonsense", 100, 100)

    with assert_raises(ValueError):
        cocotb.simulator.create_clock(dut.clk._handle, -2, 100)

    with assert_raises(ValueError):
        cocotb.simulator.create_clock(dut.clk._handle, 100, -2)

    with assert_raises(ValueError):
        cocotb.simulator.create_clock(dut.clk._handle, 100, 100, -2)

    with assert_raises(ValueError):
        cocotb.simulator.create_clock(dut.clk._handle, 100, 100, 2, -2)

    dut._log.info(repr(clk))
    assert re.match(
        r"<cocotb.simulator.sim_clock at \w+>",
        repr(clk)
    )
