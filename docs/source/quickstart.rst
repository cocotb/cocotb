.. _quickstart:

****************
Quickstart Guide
****************
The following sections describe, in short with examples, how to setup a few minimal cocotb testcases, how to run the simulation and how to view the generated waveform.
For a more thorough and complete explanations about some of the intricacies of cocotb testbenches refer to the :ref:`writing_tbs` page.

Prerequisites
=============
Before starting, install the :ref:`prerequisites<install-prerequisites>` and
cocotb itself: ``pip install cocotb``

Run ``cocotb-config --version`` in a terminal window to verify that cocotb is installed.

The examples described are made to work with the `Icarus Verilog <https://steveicarus.github.io/iverilog/>`_ simulator.
However, any other supported Verilog simulator can be used as well.
See :ref:`simulator-support` for a comprehensive list of the supported simulators.

The code for the following example is available in the cocotb sources:
:reposrc:`examples/doc_examples/quickstart <examples/doc_examples/quickstart>`.

The files can also be downloaded directly here:

   * :download:`simple_module.sv <../../examples/doc_examples/quickstart/simple_counter.sv>`
   * :download:`cocotb_test_simple_module.py <../../examples/doc_examples/quickstart/simple_counter_testcases.py>`
   * :download:`test_runner.py <../../examples/doc_examples/quickstart/test_runner.py>`
   * :download:`Makefile <../../examples/doc_examples/quickstart/Makefile>`


.. _quickstart_creating_a_test:

Creating a Test
===============
A typical cocotb testbench requires no additional :term:`HDL` code.
The :term:`DUT` is instantiated as the toplevel in the simulator without any HDL wrapper code.
The input stimulus and output checking is done in Python.

To create a cocotb testcase, the function decorator :deco:`cocotb.test()` must be used to decorate an :keyword:`async` Python function.
The decorated function must take a ``dut`` argument, this is the entry point to the HDL toplevel.

The ``dut`` argument gives access to all internals of the HDL toplevel, that is, any port, signal, parameter, as well as other submodules.
It is possible to "dot" your way through the entire hierarchy of the toplevel and access every signal inside every submodule if so desired.

.. code-block:: python3

   @cocotb.test()
   async def testcase(dut):
      do_something()

All examples described in this section can be found in the :file:`simple_counter_testcases.py` file.
The filename does not really matter as long as it is consistent with the value of :envvar:`COCOTB_TEST_MODULES` in the Makefile and the ``test_module`` argument to :meth:`cocotb_tools.Runner.test`.

.. _quickstart-example1:

Example 1 - Sequential
----------------------
In this first example there is only one sequential routine.
The routine starts by setting a default value to the ``ena`` signal,
activating the reset signal, instantiating and starting a :class:`cocotb.clock.Clock` to easily generate a clock input.
Then some time is awaited before deactivating the reset signal,
to exit out of the reset state of the ``dut``.
Then the ``ena`` signal is `activated` for 10 clock cycles,
before verifying that the counter in the module has the value 10.
Then the ``ena`` signal is `deactivated` and some time is awaited,
before checking the counter value again to verify that it was not incrementing while ``ena`` was low.

.. literalinclude:: ../../examples/doc_examples/quickstart/simple_counter_testcases.py
   :language: python
   :start-at: # Imports for all Quickstart examples
   :end-before: # QUICKSTART 1

.. literalinclude:: ../../examples/doc_examples/quickstart/simple_counter_testcases.py
   :language: python
   :start-at: # QUICKSTART 1
   :end-before: # END QUICKSTART 1

Things to note:
   * Use ``dut.`` to access anything in the HDL toplevel.
   * Use ``dut.<signal>`` to get a *reference* to a signal in the HDL toplevel.
   * Use ``dut.<signal>.value`` to get the signal *value*.
   * Use ``dut.<signal>.value = some_value`` to set the signal *value*.
   * Use :keyword:`!await` to wait for any :ref:`trigger <triggers>` (:class:`~cocotb.trigger.Timer`, :class:`~cocotb.trigger.RisingEdge`, etc.).
   * Use :keyword:`!assert` to verify that a value or condition is as expected.

Example 2 - Coroutines
----------------------
Often it is useful to have several routines running in parallel.
This can be done with :keyword:`async` functions.
In cocotb an :keyword:`!async` function should always be started with :func:`cocotb.start_soon`,
and can be :keyword:`await`-ed if desired. See :ref:`coroutines` for more information.

As long as the coroutines are not decorated with :deco:`cocotb.test` they are not automatically called
and can be used as helper functions in the actual testcase decorated with :deco:`!cocotb.test`.

The following example is similar to :ref:`quickstart-example1`,
but does continuous checking of the counter value by starting a coroutine that is always running.
Stimulus is done by starting a different coroutine.

.. literalinclude:: ../../examples/doc_examples/quickstart/simple_counter_testcases.py
   :language: python
   :start-at: # Imports for all Quickstart examples
   :end-before: # QUICKSTART 1

.. literalinclude:: ../../examples/doc_examples/quickstart/simple_counter_testcases.py
   :language: python
   :start-at: # QUICKSTART 2
   :end-before: # END QUICKSTART 2

Things to note:
   * Use :keyword:`async` to create a function that can be used as a coroutine.
   * Use :func:`cocotb.start_soon` to start a coroutine.

See the sections :ref:`writing_tbs_concurrent_sequential` and :ref:`coroutines`
for more information on such concurrent processes.


Example 3 - Reading a value can be quirky
-----------------------------------------
The :func:`cocotb.triggers.RisingEdge` trigger return precisely after the signal changes.
No sensitive processes have run to update any signals yet.
Therefore, one must await the :func:`~cocotb.triggers.ReadOnly` trigger before sampling a signal.
To escape the ReadOnly after sampling a signal, the :func:`cocotb.triggers.NextTimeStep`, among others, can be awaited.
More on this in :ref:`timing-model` chapter.


.. literalinclude:: ../../examples/doc_examples/quickstart/simple_counter_testcases.py
   :language: python
   :start-at: # Imports for all Quickstart examples
   :end-before: # QUICKSTART 1

.. literalinclude:: ../../examples/doc_examples/quickstart/simple_counter_testcases.py
   :language: python
   :start-at: # QUICKSTART 3
   :end-before: # END QUICKSTART 3

Things to note:
   * Use :func:`cocotb.triggers.ReadOnly` before sampling a signal.
   * Use :func:`cocotb.triggers.NextTimeStep` to escape the ReadOnly phase.

.. _quickstart_running_a_test:

Running a Test
==============
cocotb testcases can be run in three ways:
- Using `make <https://www.gnu.org/software/make/>`_ with a Makefile, see section :ref:`quickstart_makefile`.
- Using the :class:`cocotb_tools.runner.Runner`, see :ref:`quickstart_runner`.
- Using a self-defined custom flow, see :ref:`custom-flows`.

All the files produced during simulation end up in the :file:`sim_build/` directory unless otherwise specified.

.. _quickstart_makefile:

Makefile
---------
In order to run a test with a Makefile the following must be specified:
   * the default simulator to use (:make:var:`SIM`),
   * the default language of the toplevel module or entity (:make:var:`TOPLEVEL_LANG`, ``verilog`` in our case),
   * the design source files (:make:var:`VERILOG_SOURCES` and :make:var:`VHDL_SOURCES`),
   * the toplevel module or entity to instantiate (:envvar:`COCOTB_TOPLEVEL`, ``my_design`` in our case),
   * and Python modules that contain our cocotb tests (:envvar:`COCOTB_TEST_MODULES`.
     The file containing the test without the `.py` extension, ``simple_counter_testcases`` in our case).
   * (optional) enable waveform dumping (:make:var:`WAVES`)

.. literalinclude:: ../../examples/doc_examples/quickstart/Makefile
   :language: make
   :start-at: # Makefile


.. _quickstart_running_a_makefile:

Running a Test with a Makefile
------------------------------
The Makefile can be invoked by running:

.. code-block:: bash

   make

Icarus Verilog will be used to simulate the Verilog implementation of the DUT because
we defined these as the default values.

Values can be set in the command line to differ from the default defined in the Makefile.
For example to run the simulation with Siemens Questa and without waveform generation,
make can be invoked as follows:

.. code-block:: bash

    make SIM=questa WAVES=0


.. _quickstart_runner:

Creating a Runner
-----------------

.. warning::
    Python runners and associated APIs are an experimental feature and subject to change.

An alternative to :ref:`quickstart_makefile` is to use the :class:`cocotb_tools.Runner`, or "runner" for short.

Using the runner involves three steps:
   1. *Instantiation* of the runner with: `get_runner(sim)`
   2. *Build*, where the HDL are compiled: `runner.build(...)`
   3. *Test*, where cocotb testcases are run: `runner.test(...)`

See the section :ref:`howto-python-runner` for more details.

A minimal test runner can look like:

.. literalinclude:: ../../examples/doc_examples/quickstart/test_runner.py
   :language: python
   :start-at: # test_runner.py

Running a test with a runner
----------------------------
The test runner can be invoked by calling the ``test_simple_counter()``, in this case by running it with Python directly:

.. code-block:: bash

   python test_runner.py

However, one of the benefits of using the runner is that it can be used with `pytest <https://pytest.org>`_,
as long as the function name is discoverable by pytest, e.g. by prefixing the function with the ``test_`` prefix.
Refer to the `pytest <https://pytest.org>`_ documentation for a more comprehensive guide.

To run the cooctb test runner with pytest:

.. code-block:: bash

   pytest


Viewing the waveform
===================
To view a waveform it must be generated by the simulator, this is not enabled by default.
This "flag" can be set with :make:var:`WAVES` (``WAVES=1``) with make,
or the ``waves=True`` argument for the runner.

The generated waveform file will be located in the :file:`sim_build/` directory unless otherwise specified.
The waveform file format generated will vary depending on the simulator used.
Not all file formats are supported by all waveform viewers.
Some file formats allow easy conversion back and forth. Mileage may vary.

For simulators that do not have a built-in waveform viewer,
`GTKWave <https://gtkwave.github.io/gtkwave/index.html>`_ or the newer `Surfer <https://surfer-project.org>`_
exist as an alternative.

This example is by default using the `Icarus Verilog <https://steveicarus.github.io/iverilog/>`_ simulator.
The ``.fst`` file format is generated by default and can be opened with either GTKWave or Surfer.
