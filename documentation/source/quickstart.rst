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
See `Installing the Development Version <https://docs.cocotb.org/en/latest/install_devel.html>`_ for more details.

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

To create a cocotb test we typically create a Makefile.  Cocotb provides
rules which make it easy to get started.  We simply inform cocotb of the
source files we need compiling, the toplevel entity to instantiate and the
Python test script to load.

.. code-block:: makefile

    VERILOG_SOURCES += $(PWD)/submodule.sv
    VERILOG_SOURCES += $(PWD)/my_design.sv
    # TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file:
    TOPLEVEL = my_design
    # MODULE is the name of the Python test file:
    MODULE = test_my_design

    include $(shell cocotb-config --makefiles)/Makefile.sim

We would then create a file called ``test_my_design.py`` containing our tests.


.. _quickstart_creating_a_test:

Creating a Test
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

        dut._log.info("Running test...")
        for cycle in range(10):
            dut.clk <= 0
            await Timer(1, units="ns")
            dut.clk <= 1
            await Timer(1, units="ns")

        dut._log.info("my_signal_1 is", dut.my_signal_1.value)
        assert dut.my_signal_2.value == 0, "my_signal_2 is not 0!"

        dut._log.info("Running test...done")


This will first drive 10 periods of a square wave clock onto the ``clk`` port of the toplevel.
After this, the clock stops,
the value of ``my_signal_1`` is printed,
and the value of ``my_signal_2`` is checked to be ``0``.

Things to note:

* writing ``@cocotb.test()`` to mark this as a test to be run,
* using ``<=`` to assign a value to a signal,
* and use ``.value`` to read a value back.

The test shown is running sequentially, from start to end.
It's most likely that you will want to do things "at the same time" however
(think multiple ``always`` blocks in Verilog or ``process`` statements in VHDL).
In cocotb, you might move the clock generation part of the example above into its own
:keyword:`async` function and :func:`~cocotb.fork` it from the test:

.. code-block:: python3

    import cocotb
    from cocotb.triggers import Timer

    async def generate_clock(dut):
        """Generate clock pulses."""

        for cycle in range(10):
            dut.clk <= 0
            await Timer(1, units="ns")
            dut.clk <= 1
            await Timer(1, units="ns")

    @cocotb.test()
    async def my_second_test(dut):
        """Try accessing the design."""

        dut._log.info("Running test...")

        cocotb.fork(generate_clock(dut))  # run the clock "in the background"

        await Timer(5, units="ns")  # wait a bit, but continue while the clock is still running

        dut._log.info("my_signal_1 is", dut.my_signal_1.value)
        assert dut.my_signal_2.value == 0, "my_signal_2 is not 0!"

        dut._log.info("Running test...done")


Note that the ``generate_clock()`` function is *not* marked with ``@cocotb.test()``
since this is not a test on its own, just a helper function.

See the sections :ref:`writing_tbs_concurrent_sequential` and :ref:`coroutines`
for more information on such concurrent processes.

.. note::
   Since generating a clock is such a common task, cocotb provides a helper for it -
   :class:`cocotb.clock.Clock`.
   No need to write your own clock generator!

   You would start :class:`~cocotb.clock.Clock` with
   ``cocotb.fork(Clock(dut.clk, 1, units="ns").start())`` near the top of your test,
   after importing it with ``from cocotb.clock import Clock``.


This concludes our quick introduction to cocotb.
You can now look through our :ref:`tutorials` or check out the
:ref:`writing_tbs` chapter for more details on the above.
