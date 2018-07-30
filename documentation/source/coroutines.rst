Coroutines
==========

Testbenches built using Cocotb use coroutines. While the coroutine is executing
the simulation is paused. The coroutine uses the :keyword:`yield` keyword to
pass control of execution back to the simulator and simulation time can advance
again.

Typically coroutines :keyword:`yield` a :py:class:`Trigger` object which
indicates to the simulator some event which will cause the coroutine to be woken
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


Coroutines may also yield a list of triggers to indicate that execution should
resume if *any* of them fires:

.. code-block:: python

    @cocotb.coroutine
    def packet_with_timeout(monitor, timeout):
        """Wait for a packet but timeout if nothing arrives"""
        yield [Timer(timeout), monitor.wait_for_recv()]


The trigger that caused execution to resume is passed back to the coroutine,
allowing them to distinguish which trigger fired:

.. code-block:: python

    @cocotb.coroutine
    def packet_with_timeout(monitor, timeout):
        """Wait for a packet but timeout if nothing arrives"""
        tout_trigger = Timer(timeout)
        result = yield [tout_trigger, monitor.wait_for_recv()]
        if result is tout_trigger:
            raise TestFailure("Timed out waiting for packet")

