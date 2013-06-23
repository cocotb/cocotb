################
Quickstart Guide
################

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
    
    # Get a regerence to a register "count" in a sub-block "inst_sub_block"
    count = dut.inst_sub_block.count


Assigning values to signals
---------------------------

Values can be assigned to signals using either the .value property of a handle object or using the overloaded less than or equal to operator

.. code-block:: python
    
    # Assign the value 12 to signal "input_signal" on DUT
    dut.input_signal.value = 12
    
    # Use the overloaded less than or equal to operator
    dut.input_signal <= 12
        
        
Reading values from signals
---------------------------

Accessing the .value property of a handle object will return a :class:`BinaryValue` object.  Any unresolved bits are preserved and can be accessed using the binstr attribute, or a resolved integer value can be accessed using the value attribute.

.. code-block:: python
    
    >>> # Read a value back from the dut
    >>> count = dut.counter.value
    >>> 
    >>> print count.binstr
    1X1010
    >>> # Resolve the value (X or Z treated as 0)
    >>> print count.value
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
