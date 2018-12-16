Coroutines
==========

Testbenches built using Cocotb use coroutines. While the `coroutine` is executing
the simulation is paused. The `coroutine` uses the :keyword:`yield` keyword to
pass control of execution back to the simulator and simulation time can advance
again.

Typically coroutines :keyword:`yield` a :py:class:`Trigger` object which
indicates to the simulator some event which will cause the `coroutine` to be woken
when it occurs.  For example:

.. code-block:: python

    @cocotb.coroutine
    def wait_10ns():
        cocotb.log.info("About to wait for 10ns")
        yield Timer(10000)
        cocotb.log.info("Simulation time has advanced by 10 ns")

Coroutines may also yield other coroutines:

.. code-block:: python

    @cocotb.coroutine
    def wait_100ns():
        for i in range(10):
            yield wait_10ns()

Coroutines can return a value, so that they can be used by other coroutines.
Before python 3.3, this requires a `ReturnValue` to be raised.

.. code-block:: python

    @cocotb.coroutine
    def get_signal(clk, signal):
        yield RisingEdge(clk)
        raise ReturnValue(signal.value)

    @cocotb.coroutine
    def get_signal_python_33(clk, signal):
        # newer versions of python can use return normally
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

.. code-block:: python

    @cocotb.coroutine
    def packet_with_timeout(monitor, timeout):
        """Wait for a packet but timeout if nothing arrives"""
        yield [Timer(timeout), RisingEdge(dut.ready)]


The trigger that caused execution to resume is passed back to the `coroutine`,
allowing them to distinguish which trigger fired:

.. code-block:: python

    @cocotb.coroutine
    def packet_with_timeout(monitor, timeout):
        """Wait for a packet but timeout if nothing arrives"""
        tout_trigger = Timer(timeout)
        result = yield [tout_trigger, RisingEdge(dut.ready)]
        if result is tout_trigger:
            raise TestFailure("Timed out waiting for packet")


Coroutines can be forked for parallel operation within a function of that code and
the forked code.

.. code-block:: python
    @cocotb.test()
    def test_act_during_reset(dut):
        """ 
        while reset is active, toggle signals
        """
        tb = uart_tb(dut)
	#Clock is a built in class for toggling a clock signal
        cocotb.fork(Clock(dut.clk, 1000).start()) 
        #reset_dut is a function- part of the user generated uart_tb class. 
        cocotb.fork(tb.reset_dut(dut.rstn,20000))
    
        yield Timer(10000)
	print("Reset is still active: %d" % dut.rstn)
        yield Timer(15000)
	print("Reset has gone inactive: %d" % dut.rstn)
		

Coroutines can be joined to end parallel operation within a function.

.. code-block:: python
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

.. code-block:: python
    @cocotb.test()
    def test_different_clocks(dut):
        clk_1mhz   = Clock(dut.clk, 1.0, units='us')
        clk_250mhz = Clock(dut.clk, 4.0, units='ns')
    
        clk_gen = cocotb.fork(clk_1mhz.start())
        start_time_ns = get_sim_time(units='ns')
        yield Timer(1)
        yield RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(units='ns')
	# note, isclose is a python 3.5+ feature. 
        if not isclose(edge_time_ns, start_time_ns + 1000.0):
            raise TestFailure("Expected a period of 1 us")
    
        clk_gen.kill()
    
        clk_gen = cocotb.fork(clk_250mhz.start())
        start_time_ns = get_sim_time(units='ns')
        yield Timer(1)
        yield RisingEdge(dut.clk)
        edge_time_ns = get_sim_time(units='ns')
	# note, isclose is a python 3.5+ feature
        if not isclose(edge_time_ns, start_time_ns + 4.0):
            raise TestFailure("Expected a period of 4 ns")

