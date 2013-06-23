################
Quickstart Guide
################

A typical cocotb testbench requires no additional RTL code. The Design Under Test (DUT) is instantiated as the toplevel in the simulator without any wrapper code. Cocotb drives stimulus onto the inputs to the DUT (or further down the hierarchy) and monitors the outputs directly from Python.


Assigning values to signals
---------------------------

The Python __le__ method is overloaded to provide a convenient (and familiar to RTL developers) of assigning signals:

.. code-block:: python
   # Assign the value 12
   dut.input <= 12
        
        
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
