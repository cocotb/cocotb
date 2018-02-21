################
Test Bench Tools
################

Logging
=======

Cocotb extends the python logging library. Each dut, monitor, driver, and scoreboard (as well as any other function using the **coroutine** decorator) implements it's own :class:`logging` object, and each can be set to it's own logging level. Within a dut, each heirarchical object can also have individual logging levels set.

When logging hdl objects, beware that **_log** is the preferred way to use logging. This helps minimize the change of name collisions with an hdl log component with the python logging functionality.

Log printing levels can also be set on a per object basis. 

.. code-block:: python

        class EndianSwapperTB(object):
    
            def __init__(self, dut, debug=False):
                self.dut = dut
                self.stream_in = AvalonSTDriver(dut, "stream_in", dut.clk)
                self.stream_in_recovered = AvalonSTMonitor(dut, "stream_in", dut.clk,
                                                           callback=self.model)
    	    
                # Set verbosity on our various interfaces
                level = logging.DEBUG if debug else logging.WARNING
                self.stream_in.log.setLevel(level)
                self.stream_in_recovered.log.setLevel(level)
                self.dut.reset_n._log(setLevel(logging.DEBUG)

And when the logging is actually called

.. code-block:: python

        class AvalonSTPkts(BusMonitor):
	...
	    @coroutine
	    def _monitor_recv(self):
	        ...
                self.log.info("Received a packet of %d bytes" % len(pkt))

	class Scoreboard(object):
	    ...
	    def add_interface(self):
	        ...
                self.log.info("Created with reorder_depth %d" % reorder_depth)

        class EndianSwapTB(object):
	    ...
            @cocotb.coroutine
	    def reset():
                self.dut._log.debug("Resetting DUT")
		

will display as something like

.. code-block:: bash

    0.00ns INFO                   cocotb.scoreboard.endian_swapper_sv       scoreboard.py:177  in add_interface                   Created with reorder_depth 0    
    0.00ns DEBUG                  cocotb.endian_swapper_sv           .._endian_swapper.py:106  in reset                           Resetting DUT
    160000000000000.00ns INFO     cocotb.endian_swapper_sv.stream_out           avalon.py:151  in _monitor_recv                   Received a packet of 125 bytes

		
Busses
======

Busses are simply defined as collection of signals. The :py:class:`Bus` class will automatically bundle any group of signals together that are named similar to dut.<bus_name><seperator><signal_name>. for instance,

.. code-block:: python

        dut.stream_in_valid
        dut.stream_in_data
	
have a bus name of ``stream_in``, a seperator of ``_``, and signal names of ``valid`` and ``data``. a list of signal names, or a dictionary mapping attribute names to signal names is also passed into the :py:class:`Bus` class. Busses can have values driven onto them, be captured (returning a dictionary), or sampled and stored into a similar object. 

.. code-block:: python

		stream_in_bus = Bus(dut, "stream_in", ["valid", "data"]) # '_' is the default seperator


Driving Busses
==============

examples and specific bus implementation bus drivers (amba, avalon, xgmii, and others) exist in the :py:class:`Driver` class enabling a test to append transactions to perform the serialization of transactions onto a physical interface. Here's an example using the avalon bus driver in the endian swapper example

.. code-block:: python

    class EndianSwapperTB(object):
    
        def __init__(self, dut, debug=False):
            self.dut = dut
            self.stream_in = AvalonSTDriver(dut, "stream_in", dut.clk)
    
    def run_test(dut, data_in=None, config_coroutine=None, idle_inserter=None,
                 backpressure_inserter=None):
    
        cocotb.fork(Clock(dut.clk, 5000).start())
        tb = EndianSwapperTB(dut)
    
        yield tb.reset()
        dut.stream_out_ready <= 1
    
        if idle_inserter is not None:
            tb.stream_in.set_valid_generator(idle_inserter())
    
        # Send in the packets
        for transaction in data_in():
            yield tb.stream_in.send(transaction)
    

Monitoring Busses
=================

For our testbenches to actually be useful, we have to monitor some of these busses, and not just drive them. That's where the :py:class:`Monitor` class comes in, with prebuilt Monitors for **avalon** and **xgmii** busses. The Monitor class is a base class which you are expected to derive for your particular purpose. You must create a `_monitor_recv()` function which is responsible for determining 1) at what points in simulation to call the `_recv()` function, and 2) what transaction values to pass to be stored in the monitors receiving queue. Monitors are good for both outputs of the dut for verification, and for the inputs of the dut, to drive a test model of the dut to be compared to the actual dut. For this purpose, input monitors will often have a callback function passed that is a model. This model will often generate expected transactions, which are then compared using the **Scoreboard** class.

.. code-block:: python

    # ==============================================================================
    class BitMonitor(Monitor):
        """Observes single input or output of DUT."""
        def __init__(self, name, signal, clock, callback=None, event=None):
            self.name = name
            self.signal = signal
            self.clock = clock
            Monitor.__init__(self, callback, event)
            
        @coroutine
        def _monitor_recv(self):
            clkedge = RisingEdge(self.clock)
    
            while True:
                # Capture signal at rising edge of clock
                yield clkedge
                vec = self.signal.value
                self._recv(vec)
    
    # ==============================================================================
    def input_gen():
        """Generator for input data applied by BitDriver"""
        while True:
            yield random.randint(1,5), random.randint(1,5)
            
    # ==============================================================================
    class DFF_TB(object):
        def __init__(self, dut, init_val):
    
            self.dut = dut
    
            # Create input driver and output monitor
            self.input_drv = BitDriver(dut.d, dut.c, input_gen())
            self.output_mon = BitMonitor("output", dut.q, dut.c)
            
            # Create a scoreboard on the outputs
            self.expected_output = [ init_val ]
    
            # Reconstruct the input transactions from the pins
            # and send them to our 'model'
            self.input_mon = BitMonitor("input", dut.d, dut.c, callback=self.model)
    
        def model(self, transaction):
            """Model the DUT based on the input transaction."""
            # Do not append an output transaction for the last clock cycle of the
            # simulation, that is, after stop() has been called.
            if not self.stopped:
                self.expected_output.append(transaction)
    		

Tracking testbench errors
=========================

The :py:class:`Scoreboard` class is used to compare the actual outputs to expected outputs. Monitors are added to the scoreboard for the actual outputs, and the expected outputs can be either a simple list, or a function that provides a transaction. Here's some code from the **DFF** example, similar to above with the scoreboard added. 

.. code-block:: python
		
    class DFF_TB(object):
        def __init__(self, dut, init_val):
            self.dut = dut
    
            # Create input driver and output monitor
            self.input_drv = BitDriver(dut.d, dut.c, input_gen())
            self.output_mon = BitMonitor("output", dut.q, dut.c)
            
            # Create a scoreboard on the outputs
            self.expected_output = [ init_val ]
            self.scoreboard = Scoreboard(dut)
            self.scoreboard.add_interface(self.output_mon, self.expected_output)
    
            # Reconstruct the input transactions from the pins
            # and send them to our 'model'
            self.input_mon = BitMonitor("input", dut.d, dut.c,callback=self.model)
