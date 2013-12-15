#########
Tutorials
#########


Endian Swapper
==============

In this tutorial we'll use some of the built-in features of Cocotb to quickly create a complex testbench.

.. note:: All the code and sample output from this example are available on `EDA Playground <http://www.edaplayground.com/s/example/199>`_


Design
------

We have a relatively simplistic RTL block called the endian_swapper.  The DUT has three interfaces, all conforming to the Avalon standard:

.. image:: diagrams/svg/endian_swapper_design.svg

The dut will swap the endianness of packets on the Avalon-ST bus if a configuration bit is set.  For every packet arriving on the "stream_in" interface the entire packet will be endian swapped if the configuration bit is set, otherwise the entire packet will pass through unmodified.

Testbench
---------

To begin with we create a class to encapsulate all the common code for the testbench.  It is possible to write directed tests without using a testbench class however to encourage code re-use it is good practice to create a distinct class.


.. code-block:: python

    class EndianSwapperTB(object):
    
        def __init__(self, dut):
            self.dut = dut
            self.stream_in  = AvalonSTDriver(dut, "stream_in", dut.clk)
            self.stream_out = AvalonSTMonitor(dut, "stream_out", dut.clk)
    
            self.csr = AvalonMaster(dut, "csr", dut.clk)
    
            # Create a scoreboard on the stream_out bus
            self.expected_output = []
            self.scoreboard = Scoreboard(dut)
            self.scoreboard.add_interface(self.stream_out, self.expected_output)
    
            # Reconstruct the input transactions from the pins and send them to our 'model'
            self.stream_in_recovered = AvalonSTMonitor(dut, "stream_in", dut.clk, callback=self.model)

With the above code we have created a testbench with the following structure:

.. image:: diagrams/svg/endian_swapper_testbench.svg

If we inspect this line-by-line:

.. code-block:: python

    self.stream_in  = AvalonSTDriver(dut, "stream_in", dut.clk)

Here we're creating an AvalonSTDriver instance. The constructor requires 3 arguments - a handle to the entity containing the interface (**dut**), the name of the interface (**stream_in**) and the associated clock with which to drive the interface (**dut.clk**).  The driver will auto-discover the signals for the interface, assuming that they follow the following naming convention interface_name_signal.

In this case we have the following signals defined for the stream_in interface:

=====                   ======          =======
Name                    Type            Description (from Avalon Specification)
=====                   ======          =======
stream_in_data          data            The data signal from the source to the sink
stream_in_empty         empty           Indicates the number of symbols that are empty during cycles that contain the end of a packet
stream_in_valid         valid           Asserted by the source to qualify all other source to sink signals
stream_in_startofpacket startofpacket   Asserted by the source to mark the beginning of a packet
stream_in_endofpacket   endofpacket     Asserted by the source to mark the end of a packet
stream_in_ready         ready           Asserted high to indicate that the sink can accept data
=====                   ======          =======

By following the signal naming convention the driver can find the signals associated with this interface automatically.
