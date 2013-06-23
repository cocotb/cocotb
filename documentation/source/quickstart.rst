################
Quickstart Guide
################

A typical cocotb testbench requires no additional RTL code.
The Design Under Test (DUT) is instantiated as the toplevel in the simulator without any wrapper code.
Cocotb drives stimulus onto the inputs to the DUT (or further down the hierarchy) and monitors the outputs directly from Python.


Accessing the design
--------------------

When cocotb initialises it finds the top-level instantiation in the simulator and creates a handle called **dut**.
Top-level signals can be accessed using the "dot" notation used for accessing object attributes in Python:

.. code-block:: python

    # Get a reference to the "clk" signal on the top-level
    clk = dut.clk
    
The same notation can be used to access signals inside the design:

.. code-block:: python

   # Get a regerence to a register "count" in a sub-block "inst_sub_block"
   count = dut.inst_sub_block.count


Assigning values to signals
---------------------------

The Python __le__ method is overloaded to provide a convenient (and familiar to RTL developers) of assigning signals:

.. code-block:: python
    
    # Assign the value 12 to signal "input_signal" on DUT
    dut.input_signal.value = 12
    
    # Use the overloaded less than or equal to operator
    dut.input_signal <= 12
        
        
Reading values from signals
---------------------------



Parallel and sequential execution of coroutines
-----------------------------------------------



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
