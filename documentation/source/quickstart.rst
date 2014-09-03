################
Quickstart Guide
################


Installing cocotb
=================

Pre-requisites
--------------

Cocotb has the following requirements:

* Python 2.6+
* Python-dev packages
* A Verilog simulator


Running an example
------------------

.. code-block:: bash

    $> git clone https://github.com/potentialventures/cocotb
    $> cd cocotb
    $> make
    $> cd examples/endian_swapper
    $> make

To run a test using a different simulator:

.. code-block:: bash

    $> make SIM=vcs


Running a VHDL example
----------------------

The endian swapper example includes both a VHDL and Verilog RTL implementation.  The Cocotb testbench can execute against either implementation using VPI for Verilog and VHPI for VHDL.  To run the test suite against the VHDL implementation use the following command (a VHPI capable simulator must be used):

.. code-block:: bash

    $> make SIM=aldec GPI_IMPL=vhpi



Using cocotb
============

A typical cocotb testbench requires no additional RTL code.
The Design Under Test (DUT) is instantiated as the toplevel in the simulator without any wrapper code.
Cocotb drives stimulus onto the inputs to the DUT (or further down the hierarchy) and monitors the outputs directly from Python.


Accessing the design
--------------------

When cocotb initialises it finds the top-level instantiation in the simulator and creates a handle called **dut**.
Top-level signals can be accessed using the "dot" notation used for accessing object attributes in Python. 
The same mechanism can be used to access signals inside the design.

.. code-block:: python

    # Get a reference to the "clk" signal on the top-level
    clk = dut.clk
    
    # Get a reference to a register "count" in a sub-block "inst_sub_block"
    count = dut.inst_sub_block.count


Assigning values to signals
---------------------------

Values can be assigned to signals using either the .value property of a handle object or using direct assignment while traversing the hierarchy.

.. code-block:: python
    
    # Get a reference to the "clk" signal and assign a value
    clk = dut.clk
    clk.value = 1
    
    # Direct assignment through the hierarchy
    dut.input_signal = 12

    # Assign a value to a memory deep in the hierarchy
    dut.sub_block.memory.array[4] = 2
        
        
Reading values from signals
---------------------------

Accessing the .value property of a handle object will return a :class:`BinaryValue` object.  Any unresolved bits are preserved and can be accessed using the binstr attribute, or a resolved integer value can be accessed using the value attribute.

.. code-block:: python
    
    >>> # Read a value back from the dut
    >>> count = dut.counter.value
    >>> 
    >>> print count.binstr
    1X1010
    >>> # Resolve the value to an integer (X or Z treated as 0)
    >>> print count.integer
    42



Parallel and sequential execution of coroutines
-----------------------------------------------

.. code-block:: python

    @cocotb.coroutine
    def reset_dut(reset_n, duration):
        reset_n <= 0
        yield Timer(duration)
        reset_n <= 1
        reset_n.log.debug("Reset complete")
    
    @cocotb.test()
    def parallel_example(dut):
        reset_n = dut.reset
    
        # This will call reset_dut sequentially
        # Execution will block until reset_dut has completed
        yield reset_dut(reset_n, 500)
        dut.log.debug("After reset")
        
        # Call reset_dut in parallel with this coroutine
        reset_thread = cocotb.fork(reset_dut(reset_n, 500)
        
        yield Timer(250)
        dut.log.debug("During reset (reset_n = %s)" % reset_n.value)
        
        # Wait for the other thread to complete
        yield reset_thread.join()
        dut.log.debug("After reset")


Creating a test
---------------

.. code-block:: python

    import cocotb
    from cocotb.triggers import Timer
    
    @cocotb.test(timeout=None)
    def my_first_test(dut):
    
        # drive the reset signal on the dut
        dut.reset_n <= 0
        yield Timer(12345)
        dut.reset_n <= 1
