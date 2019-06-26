Coroutines
==========

Testbenches built using cocotb use coroutines. While the coroutine is executing
the simulation is paused. The coroutine uses the :keyword:`yield` keyword to
pass control of execution back to the simulator and simulation time can advance
again.

Typically coroutines :keyword:`yield` a :any:`Trigger` object which
indicates to the simulator some event which will cause the coroutine to be woken
when it occurs.  For example:

.. code-block:: python3

    @cocotb.coroutine
    def wait_10ns():
        cocotb.log.info("About to wait for 10ns")
        yield Timer(10000)
        cocotb.log.info("Simulation time has advanced by 10 ns")

Coroutines may also yield other coroutines:

.. code-block:: python3

    @cocotb.coroutine
    def wait_100ns():
        for i in range(10):
            yield wait_10ns()

Coroutines can return a value, so that they can be used by other coroutines.
Before Python 3.3, this requires a :any:`ReturnValue` to be raised.

.. code-block:: python3

    @cocotb.coroutine
    def get_signal(clk, signal):
        yield RisingEdge(clk)
        raise ReturnValue(signal.value)

    @cocotb.coroutine
    def get_signal_python_33(clk, signal):
        # newer versions of Python can use return normally
        yield RisingEdge(clk)
        return signal.value

    @cocotb.coroutine
    def check_signal_changes(dut):
        first = yield get_signal(dut.clk, dut.signal)
        second = yield get_signal(dut.clk, dut.signal)
        if first == second:
            raise TestFailure("Signal did not change")


Coroutines may also yield a list of triggers and coroutines to indicate that
execution should resume if *any* of them fires:

.. code-block:: python3

    @cocotb.coroutine
    def packet_with_timeout(monitor, timeout):
        """Wait for a packet but time out if nothing arrives"""
        yield [Timer(timeout), RisingEdge(dut.ready)]


The trigger that caused execution to resume is passed back to the coroutine,
allowing them to distinguish which trigger fired:

.. code-block:: python3

    @cocotb.coroutine
    def packet_with_timeout(monitor, timeout):
        """Wait for a packet but time out if nothing arrives"""
        tout_trigger = Timer(timeout)
        result = yield [tout_trigger, RisingEdge(dut.ready)]
        if result is tout_trigger:
            raise TestFailure("Timed out waiting for packet")


Coroutines can be forked for parallel operation within a function of that code and
the forked code.

.. code-block:: python3

    @cocotb.test()
    def test_act_during_reset(dut):
        """While reset is active, toggle signals"""
        tb = uart_tb(dut)
        # "Clock" is a built in class for toggling a clock signal
        cocotb.fork(Clock(dut.clk, 1000).start())
        # reset_dut is a function -
        # part of the user-generated "uart_tb" class
        cocotb.fork(tb.reset_dut(dut.rstn, 20000))

        yield Timer(10000)
        print("Reset is still active: %d" % dut.rstn)
        yield Timer(15000)
        print("Reset has gone inactive: %d" % dut.rstn)


Coroutines can be joined to end parallel operation within a function.

.. code-block:: python3

    @cocotb.test()
    def test_count_edge_cycles(dut, period=1000, clocks=6):
        cocotb.fork(Clock(dut.clk, period).start())
        yield RisingEdge(dut.clk)

        timer = Timer(period + 10)
        task = cocotb.fork(count_edges_cycles(dut.clk, clocks))
        count = 0
        expect = clocks - 1

        while True:
            result = yield [timer, task.join()]
            if count > expect:
                raise TestFailure("Task didn't complete in expected time")
            if result is timer:
                dut._log.info("Count %d: Task still running" % count)
                count += 1
            else:
                break

Coroutines can be killed before they complete, forcing their completion before
they'd naturally end.

.. code-block:: python3

    @cocotb.test()
    def test_different_clocks(dut):
        clk_1mhz   = Clock(dut.clk, 1.0, units='us')
        clk_250mhz = Clock(dut.clk, 4.0, units='ns')

        clk_gen = cocotb.fork(clk_1mhz.start())
        start_time_ns = get_sim_time(units='ns')
        yield Timer(1)
        yield RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(units='ns')
        # NOTE: isclose is a python 3.5+ feature
        if not isclose(edge_time_ns, start_time_ns + 1000.0):
            raise TestFailure("Expected a period of 1 us")

        clk_gen.kill()

        clk_gen = cocotb.fork(clk_250mhz.start())
        start_time_ns = get_sim_time(units='ns')
        yield Timer(1)
        yield RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(units='ns')
        # NOTE: isclose is a python 3.5+ feature
        if not isclose(edge_time_ns, start_time_ns + 4.0):
            raise TestFailure("Expected a period of 4 ns")

.. _async_functions:

Async functions
---------------

Python 3.5 introduces :keyword:`async` functions, which provide an alternative
syntax. For example:

.. code-block:: python3

    @cocotb.coroutine
    async def wait_10ns():
        cocotb.log.info("About to wait for 10 ns")
        await Timer(10000)
        cocotb.log.info("Simulation time has advanced by 10 ns")

To wait on a trigger or a nested coroutine, these use :keyword:`await` instead
of :keyword:`yield`. Provided they are decorated with ``@cocotb.coroutine``,
``async def`` functions using :keyword:`await` and regular functions using
:keyword:`yield` can be used interchangeable - the appropriate keyword to use
is determined by which type of function it appears in, not by the
sub-coroutinue being called.

.. note::
    It is not legal to ``await`` a list of triggers as can be done in
    ``yield``-based coroutine with ``yield [trig1, trig2]``. Use
    ``await First(trig1, trig2)`` instead.

Async generators
~~~~~~~~~~~~~~~~

In Python 3.6, a ``yield`` statement within an ``async`` function has a new
meaning (rather than being a ``SyntaxError``) which matches the typical meaning
of ``yield`` within regular python code. It can be used to create a special
type of generator function that can be iterated with ``async for``:

.. code-block:: python3

    async def ten_samples_of(clk, signal):
        for i in range(10):
            await RisingEdge(clk)
            yield signal.value  # this means "send back to the for loop"

    @cocotb.test()
    async def test_samples_are_even(dut):
        async for sample in ten_samples_of(dut.clk, dut.signal):
            assert sample % 2 == 0

More details on this type of generator can be found in :pep:`525`.

