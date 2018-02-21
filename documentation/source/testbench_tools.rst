################
Test Bench Tools
################

Logging
=======

Cocotb extends the python logging library. Each dut, monitor, driver, and scoreboard (as well as any other function using the **coroutine** decorator) implements it's own logging object, and each can be set to it's own logging level.

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


And when the logging is actually called

.. code-block:: python

        class AvalonSTPkts(BusMonitor):
	...
	@coroutine
	def _monitor_recv(self):
	    ...
            self.log.info("Received a packet of %d bytes" % len(pkt))
        @cocotb.coroutine
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

    0.00ns INFO     cocotb.scoreboard.endian_swapper_sv       scoreboard.py:177  in add_interface                   Created with reorder_depth 0    
    0.00ns DEBUG    cocotb.endian_swapper_sv           .._endian_swapper.py:106  in reset                           Resetting DUT
    160000000000000.00ns INFO     cocotb.endian_swapper_sv.stream_out           avalon.py:151  in _monitor_recv                   Received a packet of 125 bytes

		
Buses
=====

Busses are simply defined as collection of signals. The **Bus** class will automatically bundle any group of signals together that are named similar to dut.<bus_name><seperator><signal_name>. for instance,
    dut.stream_in_valid
    dut.stream_in_data
have a bus name of ``stream_in``, a seperator of ``_``, and signal names of ``valid`` and ``data``. a list of signal names, or a dictionary mapping attribute names to signal names is also passed into the **Bus** class. Busses can have values driven onto them, be captured (returning a dictionary), or sampled and stored into a similar object. 


Driving Busses
==============

examples and specific bus implementation bus drivers (amba, avalon, xgmii, and others) exist in the **Driver** class enabling a test to append transactions to perform the serialization of transactions onto a physical interface.


Monitoring Busses
=================

For our testbenches to actually be useful, we have to monitor some of these busses, and not just drive them. That's where the **Monitor** class comes in, with prebuilt Monitors for ``avalon`` and ``xgmii`` busses. The Monitor class is a base class which you are expected to derive for your particular purpose. You must create a `_monitor_recv()` function which is responsible for determining 1) at what points in simulation to call the `_recv()` function, and 2) what transaction values to pass to be stored in the monitors receiving queue. Monitors are good for both outputs of the dut for verification, and for the inputs of the dut, to drive a test model of the dut to be compared to the actual dut. For this purpose, input monitors will often have a callback function passed that is a model. This model will often generate expected transactions, which are then compared using the **Scoreboard** class. 

Tracking testbench errors
=========================

The **Scoreboard** class is used to compare the actual outputs to expected outputs. Monitors are added to the scoreboard for the actual outputs, and the expected outputs can be either a simple list, or a function that provides a transaction. 
