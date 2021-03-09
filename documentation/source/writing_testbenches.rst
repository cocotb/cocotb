.. _writing_tbs:

*******************
Writing Testbenches
*******************


.. _writing_tbs_accessing_design:

Accessing the design
====================

When cocotb initializes it finds the toplevel instantiation in the simulator
and creates a handle called ``dut``. Toplevel signals can be accessed using the
"dot" notation used for accessing object attributes in Python. The same mechanism
can be used to access signals inside the design.

.. code-block:: python3

    # Get a reference to the "clk" signal on the toplevel
    clk = dut.clk

    # Get a reference to a register "count"
    # in a sub-block "inst_sub_block"
    count = dut.inst_sub_block.count


.. _writing_tbs_assigning_values:

Assigning values to signals
===========================

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

.. _writing_tbs_assigning_values_signed_unsigned:

Signed and unsigned values
--------------------------

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


.. _writing_tbs_reading_values:

Reading values from signals
===========================

Values in the DUT can be accessed with the :attr:`~cocotb.handle.NonHierarchyObject.value`
property of a handle object.
A common mistake is forgetting the ``.value`` which just gives you a reference to a handle
(useful for defining an alias name), not the value.

The Python type of a value depends on the handle's HDL type:

* Arrays of ``logic`` and subtypes of that (``sfixed``, ``unsigned``, etc.)
  are of type :class:`~cocotb.binary.BinaryValue`.
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


.. _writing_tbs_concurrent_sequential:

Concurrent and sequential execution
===================================

An :keyword:`await` will run an :keyword:`async` coroutine and wait for it to complete.
The called coroutine "blocks" the execution of the current coroutine.
Wrapping the call in :func:`~cocotb.fork` runs the coroutine concurrently,
allowing the current coroutine to continue executing.
At any time you can :keyword:`await` the result of the forked coroutine,
which will block until the forked coroutine finishes.

The following example shows these in action:

.. code-block:: python3

    # A coroutine
    async def reset_dut(reset_n, duration_ns):
        reset_n <= 0
        await Timer(duration_ns, units="ns")
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
        await Timer(250, units="ns")
        dut._log.debug("During reset (reset_n = %s)" % reset_n.value)

        # Wait for the other thread to complete
        await reset_thread
        dut._log.debug("After reset")

See :ref:`coroutines` for more examples of what can be done with coroutines.


.. _writing_tbs_assigning_values_forcing_freezing:

Forcing and freezing signals
============================

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


.. _writing_tbs_accessing_underscore_identifiers:

Accessing Identifiers Starting with an Underscore
=================================================

The attribute syntax of ``dut._some_signal`` cannot be used to access
an identifier that starts with an underscore (``_``, as is valid in Verilog)
because we reserve such names for cocotb-internals,
thus the access will raise an :exc:`AttributeError`.

A workaround is to use indirect access using
:meth:`~cocotb.handle.HierarchyObject._id` like in the following example:
``dut._id("_some_signal", extended=False)``.

Logging
=======

Cocotb uses the builtin :mod:`logging` library, with some configuration described in :ref:`logging-reference-section` to provide some sensible defaults.
Any forked coroutine holds a :class:`logging.Logger`,
and can be set to its own logging level.

.. code-block:: python3

    task = cocotb.fork(coro)
    task.log.setLevel(logging.DEBUG)
    task.log.debug("Running Task!")

The :term:`DUT` and each hierarchical object can also have individual logging levels set.
When logging :term:`HDL` objects, beware that ``_log`` is the preferred way to use
logging. This helps minimize the change of name collisions with an :term:`HDL` log
component with the Python logging functionality.

.. code-block:: python3

    dut.my_signal._log.info("Setting signal")
    dut.my_signal <= 1
