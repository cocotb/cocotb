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

