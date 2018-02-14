################
Test Bench Tools
################

Logging
=======

Cocotb extends the python logging library. Each dut, monitor, driver, and scoreboard (as well as any other function using the **coroutine** decorator) implements it's own logging object, and each can be set to it's own logging level.

When logging hdl objects, beware that **_log** is the preferred way to use logging. This helps minimize the change of name collisions with an hdl log component with the python logging functionality. 

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
