.. _writing_tbs:

*******************
Writing Testbenches
*******************


Logging
=======

Cocotb uses Python's :mod:`logging` library, with the configuration described in :ref:`logging-reference-section` to provide some sensible defaults.
``cocotb.log.info`` is a good stand-in for :func:`print`,
but user are encouraged to create their own loggers and logger hierarchy by calling :func:`logging.getLogger` and/or :meth:`.Logger.getChild`.

Logging functions `only` log messages, they do not cause the test to fail.
See :ref:`passing_and_failing_tests` for more information on how to fail a test.

.. code-block:: python

    import logging
    import cocotb

    @cocotb.test()
    async def test(dut):
        # Create a logger for this testbench
        logger = logging.getLogger("my_testbench")

        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")
        logger.critical("This is a critical message")

.. note::

    Writing messages to the log/console using the built-in function :func:`print` is not recommended in cocotb testbenches.
    :func:`print` defaults to writing to ``stdout``, which is often buffered;
    not only by the Python runtime, but sometimes by the simulator as well.
    This can make messages appear out-of-order compared to messages coming from the simulator or the :term:`DUT`.

.. warning::

    The ``"cocotb"`` and ``"gpi"`` logger namespaces and all :class:`~logging.Logger`\ s on cocotb-created objects are reserved for internal use only.


.. _writing_tbs_accessing_design:

Accessing the design
====================

When cocotb initializes it finds the toplevel instantiation in the simulator
and creates a *handle* called ``dut``. Toplevel signals can be accessed using the
"dot" notation used for accessing object attributes in Python. The same mechanism
can be used to access signals inside the design.

.. code-block:: python

    # Get a reference to the "clk" signal on the toplevel
    clk = dut.clk

    # Get a reference to a register "count"
    # in a sub-block "inst_sub_block"
    # (the instance name of a Verilog module or VHDL entity/component)
    count = dut.inst_sub_block.count


.. _writing_tbs_finding_elements:

Finding elements in the design
==============================

To find elements of the DUT
(for example, instances, signals, constants or Verilog packages)
at a certain hierarchy level,
you can use the :func:`dir` function on a handle.

.. code-block:: python

    # Print the instances and signals (which includes the ports) of the design's toplevel
    cocotb.log.info(dir(dut))

    # Print the instances and signals of "inst_sub_block" under the toplevel
    # which is the instance name of a Verilog module or VHDL entity/component
    cocotb.log.info(dir(dut.inst_sub_block))

    # Print the packages
    cocotb.log.info(dir(cocotb.packages))


.. _writing_tbs_assigning_values:

Assigning values to signals
===========================

Values can be assigned to signals using either the
:attr:`~cocotb.handle.ValueObjectBase.value` property of a handle object
or :meth:`~cocotb.handle.ValueObjectBase.set` method of a handle object.

.. code-block:: python

    # Get a reference to the "clk" signal and assign a value
    clk = dut.clk
    clk.value = 1

    # Direct assignment through the hierarchy
    dut.input_signal.value = 12

    # Assign a value to a memory deeper in the hierarchy
    # ("inst_sub_block" and "inst_memory" are instance names of the
    # respective Verilog modules or VHDL entity/components in the DUT)
    dut.inst_sub_block.inst_memory.mem_array[4].value = 2


The assignment syntax ``sig.value = new_value`` has the same semantics as :term:`HDL`:
writes are not applied immediately, but delayed until the next write cycle.
Use :class:`~cocotb.handle.Immediate` to set a new value immediately.

.. _writing_tbs_assigning_values_signed_unsigned:

Signed and unsigned values
--------------------------

Both signed and unsigned values can be assigned to signals using a Python int.
Cocotb makes no assumptions regarding the signedness of the signal. It only
considers the width of the signal, so it will allow values in the range from
the minimum negative value for a signed number up to the maximum positive
value for an unsigned number: ``-2**(Nbits - 1) <= value <= 2**Nbits - 1``
Note: assigning out-of-range values will raise an :exc:`ValueError`.

A :class:`~cocotb.types.LogicArray` object can be used instead of a Python int to assign a
value to signals with more fine-grained control (e.g. signed values only).

.. code-block:: verilog

    module my_module (
        input   logic       clk,
        input   logic       rst,
        input   logic [2:0] data_in,
        output  logic [2:0] data_out
        );

.. code-block:: python

    # assignment of negative value
    dut.data_in.value = -4

    # assignment of positive value
    dut.data_in.value = 7

    # assignment of out-of-range values
    dut.data_in.value = 8   # raises ValueError
    dut.data_in.value = -5  # raises ValueError


.. _writing_tbs_reading_values:

Reading values from signals
===========================

Values in the DUT can be accessed with the :attr:`~cocotb.handle.ValueObjectBase.value`
property of a handle object.
A common mistake is forgetting the ``.value`` which just gives you a reference to a handle
(useful for defining an alias name), not the value.

The Python type of a value depends on the handle's HDL type:

* Arrays of ``logic`` and subtypes of that (``sfixed``, ``unsigned``, etc.)
  are of type :class:`~cocotb.types.LogicArray`.
* Integer nets and constants (``integer``, ``natural``, etc.) return :class:`int`.
* Floating point nets and constants (``real``) return :class:`float`.
* Boolean nets and constants (``boolean``) return :class:`bool`.
* String nets and constants (``string``) return :class:`bytes`.

.. todo::
    Add simple example of how to use LogicArray


.. _writing_tbs_identifying_tests:

Identifying tests
=================

Cocotb tests are identified using the :class:`~cocotb.test` decorator.
Using this decorator will tell cocotb that this function is a special type of coroutine that is meant
to either pass or fail.
The :class:`~cocotb.test` decorator supports several keyword arguments (see section :ref:`writing-tests`).
In most cases no arguments are passed to the decorator so cocotb tests can be written as:

.. code-block:: python

    # A valid cocotb test
    @cocotb.test
    async def test(dut):
        pass

    # Also a valid cocotb test
    @cocotb.test()
    async def test(dut):
        pass

.. _writing_tbs_concurrent_sequential:

Concurrent and sequential execution
===================================

An :keyword:`await` will run an :keyword:`async` coroutine and wait for it to complete.
The called coroutine "blocks" the execution of the current coroutine.
Wrapping the call in :func:`~cocotb.start_soon` runs the coroutine concurrently,
allowing the current coroutine to continue executing.
At any time you can await the result of a :class:`~cocotb.task.Task`,
which will block the current coroutine's execution until the task finishes.

The following example shows these in action:

.. code-block:: python

    # A coroutine
    async def reset_dut(reset_n, duration_ns):
        reset_n.value = 0
        await Timer(duration_ns, unit="ns")
        reset_n.value = 1
        cocotb.log.debug("Reset complete")

    @cocotb.test()
    async def parallel_example(dut):
        reset_n = dut.reset

        # Execution will block until reset_dut has completed
        await reset_dut(reset_n, 500)
        cocotb.log.debug("After reset")

        # Run reset_dut concurrently
        reset_thread = cocotb.start_soon(reset_dut(reset_n, duration_ns=500))

        # This timer will complete before the timer in the concurrently executing "reset_thread"
        await Timer(250, unit="ns")
        cocotb.log.debug("During reset (reset_n = %s)" % reset_n.value)

        # Wait for the other thread to complete
        await reset_thread
        cocotb.log.debug("After reset")

See :ref:`coroutines` for more examples of what can be done with coroutines.


.. _writing_tbs_assigning_values_forcing_freezing:

Forcing and freezing signals
============================

In addition to regular value assignments (deposits), signals can be forced
to a predetermined value or frozen at their current value. To achieve this,
the various actions described in :ref:`assignment-methods` can be used.

.. autolink-preface:: from cocotb.handle import Deposit, Force, Freeze, Release
.. code-block:: python

    # Deposit action
    dut.my_signal.value = 12
    dut.my_signal.value = Deposit(12)  # equivalent syntax

    # Force action
    dut.my_signal.value = Force(12)    # my_signal stays 12 until released

    # Release action
    dut.my_signal.value = Release()    # Reverts any force/freeze assignments

    # Freeze action
    dut.my_signal.value = Freeze()     # my_signal stays at current value until released

.. warning::

    Not all simulators support these features; refer to the :ref:`simulator-support` section for details or to `issues with label "upstream" <https://github.com/cocotb/cocotb/issues?q=is%3Aissue+-label%3Astatus%3Aduplicate+label%3Aupstream>`_


.. _writing_tbs_accessing_underscore_identifiers:

Accessing identifiers starting with an underscore or invalid Python names
=========================================================================

The attribute syntax of ``dut._some_signal`` cannot be used to access
an identifier that starts with an underscore (``_``, as is valid in Verilog)
because we reserve such names for cocotb-internals,
thus the access will raise an :exc:`AttributeError`.

Both SystemVerilog and VHDL allow developers to create signals or nets with non-standard characters by using special syntax.
These objects are generally not accessible using attribute syntax since attributes in Python must follow a strict form.

All named objects, including those with the aforementioned limitations, can be accessed using index syntax.

.. code-block:: python

    dut["_some_signal"]  # begins with underscore
    dut["\\!WOOOOW!\\"]  # escaped identifier (Verilog), extended identifier (VHDL)


.. _writing_tbs_accessing_verilog_packages:

Accessing Verilog packages
==========================

Verilog packages are accessible via :data:`cocotb.packages`.
Depending on the simulator, packages may need to be imported in
the compilation unit scope or inside a module in order to be discoverable.
Also note, the ``$unit`` pseudo-package is implemented differently between simulators.
It may appear as one or more attributes here depending on the number of compilation units.

.. code-block:: verilog

    package my_package;
        parameter int foo = 7
    endpackage

.. code-block:: python

    # prints "7"
    cocotb.log.info(cocotb.packages.my_package.foo.value)


.. _passing_and_failing_tests:

Passing and failing tests
=========================

A cocotb test is considered to have `failed` if the test coroutine or any running :class:`~cocotb.task.Task`
fails an :keyword:`assert` statement.
Below are examples of `failing` tests.

.. code-block:: python

    @cocotb.test()
    async def test(dut):
        assert 1 > 2, "Testing the obvious"

    @cocotb.test()
    async def test(dut):
        async def fails_test():
            assert 1 > 2
        cocotb.start_soon(fails_test())
        await Timer(10, 'ns')

When a test fails, a stacktrace is printed.
If :mod:`pytest` is installed and assert statements are used,
a more informative stacktrace is printed which includes the values that caused the assert to fail.
For example, see the output for the first test from above.

.. code-block::

    0.00ns ERROR    Test Failed: test (result was AssertionError)
                    Traceback (most recent call last):
                      File "test.py", line 3, in test
                        assert 1 > 2, "Testing the obvious"
                    AssertionError: Testing the obvious


A cocotb test is considered to have `errored` if the test coroutine or any running :class:`~cocotb.task.Task`
raises an exception that isn't considered a `failure`.
Below are examples of `erroring` tests.

.. code-block:: python

    @cocotb.test()
    async def test(dut):
        await coro_that_does_not_exist()  # NameError

    @cocotb.test()
    async def test(dut):
        async def coro_with_an_error():
            dut.signal_that_does_not_exist.value = 1  # AttributeError
        cocotb.start_soon(coro_with_an_error())
        await Timer(10, 'ns')

When a test ends with an error, a stacktrace is printed.
For example, see the below output for the first test from above.

.. code-block::

    0.00ns ERROR    Test Failed: test (result was NameError)
                    Traceback (most recent call last):
                      File "test.py", line 3, in test
                        await coro_that_does_not_exist()  # NameError
                    NameError: name 'coro_that_does_not_exist' is not defined


If a test coroutine completes without `failing` or `erroring`,
or if the test coroutine or any running :class:`~cocotb.task.Task` calls :func:`~cocotb.pass_test`,
the test is considered to have `passed`.
Below are examples of `passing` tests.

.. code-block:: python

    @cocotb.test()
    async def test(dut):
        assert 2 > 1  # assertion is correct, then the coroutine ends

    @cocotb.test()
    async def test(dut):
        cocotb.pass_test("Reason")  # ends test with success early
        assert 1 > 2  # this would fail, but it isn't run because the test was ended early

    @cocotb.test()
    async def test(dut):
        async def ends_test_with_pass():
            cocotb.pass_test("Reason")
        cocotb.start_soon(ends_test_with_pass())
        await Timer(10, 'ns')

A passing test will print the following output.

.. code-block::

    0.00ns INFO     Test Passed: test


Cleaning up resources
=====================

When you call :meth:`.Task.cancel` on a Task,
a :exc:`CancelledError` will be raised which can be caught to run cleanup or end-of-test code.
This will also trigger the finalization routine of any :term:`context manager`.

When a test ends, the cocotb runtime will call :meth:`.Task.cancel` on all running tasks started with :func:`cocotb.start_soon`,
allowing for end-of-test cleanup.

.. code-block:: python

    @cocotb.test()
    async def test(dut):

        async def drive_data_valid(intf, sequence):
            try:
                intf.valid.value = 1
                for data in sequence:
                    intf.data.value = data
            finally:
                # Ensure that valid is brought back to 0 when the test ends,
                # the Task is explicitly cancelled, or if the Task ends normally.
                intf.valid.value = 0

        # Generate sequence
        sequence = ...

        # Run driver Task concurrently
        cocotb.start_soon(drive_data_valid(dut.data_in, sequence))

        # Do other stuff

.. note::
    If a :exc:`!CancelledError` is handled and not re-raised, the test will be considered to have failed.
    For that reason, it is recommended to use :keyword:`finally` rather than specifically catching :exc:`!CancelledError`.
