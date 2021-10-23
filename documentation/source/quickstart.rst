.. _quickstart:

****************
Quickstart Guide
****************

In the following sections,
we are walking you through creating and running a small but complete cocotb testbench
for a fictional *Design Under Test* (:term:`DUT`) called ``my_design``.

Please install the :ref:`prerequisites<install-prerequisites>`
and cocotb itself (``pip install cocotb``) now.
Run ``cocotb-config --version`` in a terminal window to check that cocotb is correctly installed.

The code for the following example is available as
:reposrc:`examples/doc_examples/quickstart <examples/doc_examples/quickstart>`
in the cocotb sources.
You can also download the files here:
:download:`my_design.sv <../../examples/doc_examples/quickstart/my_design.sv>`,
:download:`test_my_design.py <../../examples/doc_examples/quickstart/test_my_design.py>`,
:download:`Makefile <../../examples/doc_examples/quickstart/Makefile>`.


.. _quickstart_creating_a_test:

Creating a Test
===============

A typical cocotb testbench requires no additional :term:`HDL` code.
The :term:`DUT` is instantiated as the toplevel in the simulator
without any HDL wrapper code.

The test is written in Python.

In cocotb, you can access all internals of your design,
e.g. signals, ports, parameters, etc. through an object that is passed to each test.
In the following we'll call this object ``dut``.

Let's create a test file ``test_my_design.py`` containing the following:

.. literalinclude:: ../../examples/doc_examples/quickstart/test_my_design.py
   :language: python3
   :start-at: # test_my_design.py (simple)
   :end-before: # test_my_design.py (extended)

This will first drive 10 periods of a square wave clock onto a port ``clk`` of the toplevel.
After this, the clock stops,
the value of ``my_signal_1`` is printed,
and the value of index ``0`` of ``my_signal_2`` is checked to be ``0``.

Things to note:

* Use the ``@cocotb.test()`` decorator to mark the test function to be run.
* Use ``.value = value`` to assign a value to a signal.
* Use ``.value`` to get a signal's current value.

The test shown is running sequentially, from start to end.
Each :keyword:`await` expression suspends execution of the test until
whatever event the test is waiting for occurs and the simulator returns
control back to cocotb (see :ref:`simulator-triggers`).

It's most likely that you will want to do several things "at the same time" however -
think multiple ``always`` blocks in Verilog or ``process`` statements in VHDL.
In cocotb, you might move the clock generation part of the example above into its own
:keyword:`async` function and :func:`~cocotb.start` it ("start it in the background")
from the test:

.. literalinclude:: ../../examples/doc_examples/quickstart/test_my_design.py
   :language: python3
   :start-at: # test_my_design.py (extended)

Note that the ``generate_clock()`` function is *not* marked with ``@cocotb.test()``
since this is not a test on its own, just a helper function.

See the sections :ref:`writing_tbs_concurrent_sequential` and :ref:`coroutines`
for more information on such concurrent processes.

.. note::
   Since generating a clock is such a common task, cocotb provides a helper for it -
   :class:`cocotb.clock.Clock`.
   No need to write your own clock generator!

   You would start :class:`~cocotb.clock.Clock` with
   ``cocotb.start_soon(Clock(dut.clk, 1, units="ns").start())`` near the top of your test,
   after importing it with ``from cocotb.clock import Clock``.


.. _quickstart_creating_a_makefile:

Creating a Makefile
===================

In order to run a test,
you create a ``Makefile`` that contains information about your project
(i.e. the specific DUT and test).

In the ``Makefile`` shown below we specify:

* the default simulator to use (:make:var:`SIM`),
* the default language of the toplevel module or entity (:make:var:`TOPLEVEL_LANG`, ``verilog`` in our case),
* the design source files (:make:var:`VERILOG_SOURCES` and :make:var:`VHDL_SOURCES`),
* the toplevel module or entity to instantiate (:envvar:`TOPLEVEL`, ``my_design`` in our case),
* and a Python module that contains our cocotb tests (:envvar:`MODULE`.
  The file containing the test without the `.py` extension, ``test_my_design`` in our case).

.. literalinclude:: ../../examples/doc_examples/quickstart/Makefile
   :language: make
   :start-at: # Makefile


.. _quickstart_running_a_test:

Running a Test
==============

When you now type

.. code-block:: bash

   make

Icarus Verilog will be used to simulate the Verilog implementation of the DUT because
we defined these as the default values.

If you want to simulate the DUT with Siemens Questa instead,
all you would need to change is the command line:

.. code-block:: bash

    make SIM=questa


This concludes our quick introduction to cocotb.
You can now look through our Tutorials or check out the
:ref:`writing_tbs` chapter for more details on the above.
