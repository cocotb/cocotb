.. _quickstart:

****************
Quickstart Guide
****************


Running your first Example
==========================

Make sure you have the :ref:`prerequisites<install-prerequisites>`
(Python with development packages, a C++11 compiler with development packages, GNU Make,
a :ref:`supported simulator<simulator-support>`) and cocotb itself (``pip install cocotb``) available.

Download and extract the cocotb source files according to the *release version* you are using from
https://github.com/cocotb/cocotb/releases - you can check your cocotb version with ``cocotb-config --version``.

The sources for cocotb's *development version* are available from https://github.com/cocotb/cocotb.
See :ref:`install-devel` for more details.

The following lines are all you need to run a first simulation with cocotb:

.. code-block:: bash

    cd cocotb/examples/simple_dff
    make

This was running with the default simulator, Icarus Verilog,
but selecting a different simulator is as easy as:

.. code-block:: bash

    make SIM=vcs


Running the same example as VHDL
--------------------------------

The ``simple_dff`` example includes both a VHDL and a Verilog :term:`RTL` implementation.
The cocotb testbench can execute against either implementation using :term:`VPI` for
Verilog and :term:`VHPI`/:term:`FLI` for VHDL.  To run the test suite against the VHDL
implementation, use the following command (a :term:`VHPI` or :term:`FLI` capable simulator must
be used):

.. code-block:: bash

    make SIM=ghdl TOPLEVEL_LANG=vhdl


Using cocotb
============

A typical cocotb testbench requires no additional :term:`HDL` code (though nothing prevents you from adding testbench helper code).
The Design Under Test (:term:`DUT`) is instantiated as the toplevel in the simulator
without any wrapper code.
Cocotb drives stimulus onto the inputs to the :term:`DUT` and monitors the outputs
directly from Python.


Creating a Makefile
-------------------

To create a cocotb test we typically have to create a Makefile.  Cocotb provides
rules which make it easy to get started.  We simply inform cocotb of the
source files we need compiling, the toplevel entity to instantiate and the
Python test script to load.

.. code-block:: makefile

    VERILOG_SOURCES = $(PWD)/submodule.sv $(PWD)/my_design.sv
    # TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file:
    TOPLEVEL=my_design
    # MODULE is the name of the Python test file:
    MODULE=test_my_design

    include $(shell cocotb-config --makefiles)/Makefile.sim

We would then create a file called ``test_my_design.py`` containing our tests.


.. _quickstart_creating_a_test:

Creating a test
---------------

The test is written in Python. Cocotb wraps your top level with the handle you
pass it. In this documentation, and most of the examples in the project, that
handle is ``dut``, but you can pass your own preferred name in instead. The
handle is used in all Python files referencing your :term:`RTL` project. Assuming we
have a toplevel port called ``clk`` we could create a test file containing the
following:

.. code-block:: python3

    import cocotb
    from cocotb.triggers import Timer

    @cocotb.test()
    async def my_first_test(dut):
        """Try accessing the design."""

        dut._log.info("Running test!")
        for cycle in range(10):
            dut.clk <= 0
            await Timer(1, units='ns')
            dut.clk <= 1
            await Timer(1, units='ns')
        dut._log.info("Running test!")

This will drive a square wave clock onto the ``clk`` port of the toplevel.


Accessing the design
--------------------

When cocotb initializes it finds the top-level instantiation in the simulator
and creates a handle called ``dut``. Top-level signals can be accessed using the
"dot" notation used for accessing object attributes in Python. The same mechanism
can be used to access signals inside the design.

.. code-block:: python3

    # Get a reference to the "clk" signal on the top-level
    clk = dut.clk

    # Get a reference to a register "count"
    # in a sub-block "inst_sub_block"
    count = dut.inst_sub_block.count


Assigning values to signals
---------------------------

Values can be assigned to signals using either the
:attr:`~cocotb.handle.NonHierarchyObject.value` property of a handle object
or using direct assignment while traversing the hierarchy.

.. code-block:: python3

    # Get a reference to the "clk" signal and assign a value
    clk = dut.clk
    clk.value = 1

    # Direct assignment through the hierarchy
    dut.input_signal <= 12

    # Assign a value to a memory deep in the hierarchy
    dut.sub_block.memory.array[4] <= 2


The syntax ``sig <= new_value`` is a short form of ``sig.value = new_value``.
It not only resembles :term:`HDL` syntax, but also has the same semantics:
writes are not applied immediately, but delayed until the next write cycle.
Use ``sig.setimmediatevalue(new_val)`` to set a new value immediately
(see :meth:`~cocotb.handle.NonHierarchyObject.setimmediatevalue`).

Signed and unsigned values
^^^^^^^^^^^^^^^^^^^^^^^^^^

Both signed and unsigned values can be assigned to signals using a Python int.
Cocotb makes no assumptions regarding the signedness of the signal. It only
considers the width of the signal, so it will allow values in the range from
the minimum negative value for a signed number up to the maximum positive
value for an unsigned number: ``-2**(Nbits - 1) <= value <= 2**Nbits - 1``
Note: assigning out-of-range values will raise an :exc:`OverflowError`.

A :class:`BinaryValue` object can be used instead of a Python int to assign a
value to signals with more fine-grained control (e.g. signed values only).

.. code-block:: verilog

    module my_module (
        input   logic       clk,
        input   logic       rst,
        input   logic [2:0] data_in,
        output  logic [2:0] data_out
        );

.. code-block:: python3

    # assignment of negative value
    dut.data_in <= -4

    # assignment of positive value
    dut.data_in <= 7

    # assignment of out-of-range values
    dut.data_in <= 8   # raises OverflowError
    dut.data_in <= -5  # raises OverflowError

Forcing and freezing signals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In addition to regular value assignments (deposits), signals can be forced
to a predetermined value or frozen at their current value. To achieve this,
the various actions described in :ref:`assignment-methods` can be used.

.. code-block:: python3

    # Deposit action
    dut.my_signal <= 12
    dut.my_signal <= Deposit(12)  # equivalent syntax

    # Force action
    dut.my_signal <= Force(12)    # my_signal stays 12 until released

    # Release action
    dut.my_signal <= Release()    # Reverts any force/freeze assignments

    # Freeze action
    dut.my_signal <= Freeze()     # my_signal stays at current value until released


.. _quickstart_reading_values:

Reading values from signals
---------------------------

Values in the DUT can be accessed with the :attr:`~cocotb.handle.NonHierarchyObject.value`
property of a handle object.
A common mistake is forgetting the ``.value`` which just gives you a reference to a handle
(useful for defining an alias name), not the value.

The Python type of a value depends on the handle's HDL type:

* Arrays of ``logic`` and subtypes of that (``sfixed``, ``unsigned``, etc.) are of type :class:`~cocotb.binary.BinaryValue`.
* Integer nets and constants (``integer``, ``natural``, etc.) return :class:`int`.
* Floating point nets and constants (``real``) return :class:`float`.
* Boolean nets and constants (``boolean``) return :class:`bool`.
* String nets and constants (``string``) return :class:`bytes`.

For a :class:`~cocotb.binary.BinaryValue` object, any unresolved bits are preserved and
can be accessed using the :attr:`~cocotb.binary.BinaryValue.binstr` attribute,
or a resolved integer value can be accessed using the :attr:`~cocotb.binary.BinaryValue.integer` attribute.

.. code-block:: pycon

    >>> # Read a value back from the DUT
    >>> count = dut.counter.value
    >>> print(count.binstr)
    1X1010
    >>> # Resolve the value to an integer (X or Z treated as 0)
    >>> print(count.integer)
    42
    >>> # Show number of bits in a value
    >>> print(count.n_bits)
    6

We can also cast the signal handle directly to an integer:

.. code-block:: pycon

    >>> print(int(dut.counter))
    42


Parallel and sequential execution
---------------------------------

An :keyword:`await` will run an :keyword:`async` coroutine and wait for it to complete.
The called coroutine "blocks" the execution of the current coroutine.
Wrapping the call in :func:`~cocotb.fork` runs the coroutine concurrently, allowing the current coroutine to continue executing.
At any time you can :keyword:`await` the result of the forked coroutine, which will block until the forked coroutine finishes.

The following example shows these in action:

.. code-block:: python3

    # A coroutine
    async def reset_dut(reset_n, duration_ns):
        reset_n <= 0
        await Timer(duration_ns, units='ns')
        reset_n <= 1
        reset_n._log.debug("Reset complete")

    @cocotb.test()
    async def parallel_example(dut):
        reset_n = dut.reset

        # Execution will block until reset_dut has completed
        await reset_dut(reset_n, 500)
        dut._log.debug("After reset")

        # Run reset_dut concurrently
        reset_thread = cocotb.fork(reset_dut(reset_n, duration_ns=500))

        # This timer will complete before the timer in the concurrently executing "reset_thread"
        await Timer(250, units='ns')
        dut._log.debug("During reset (reset_n = %s)" % reset_n.value)

        # Wait for the other thread to complete
        await reset_thread
        dut._log.debug("After reset")

See :ref:`coroutines` for more examples of what can be done with coroutines.
