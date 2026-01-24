###########
First Steps
###########

This tutorial will walk you through the verification of a simple hardware counter.
This will include:

* Creating a Makefile to build your design and run simulations.
* Defining a cocotb test.
* Accessing objects in the design under test (:term:`DUT`).
* Waiting for events.
* Performing actions concurrently.
* Passing and failing tests.
* Viewing the waveforms after a simulation.

.. warning::
    Make sure you are reading the version of the documentation that matches the version of cocotb you have installed.
    And if you are downloading the example files, make sure they are from the same tagged release as well.


Prerequisites
=============
Before starting, :ref:`install cocotb <install>` if you have not already done so.

Verify cocotb was installed correctly by running the ``cocotb-config --version`` command.
If you see it print the version number, then cocotb is installed and ready to use.
If not, you may need to adjust your Python environment or cocotb installation.

.. TODO add troubleshooting documentation?

This tutorial uses `Icarus Verilog <https://steveicarus.github.io/iverilog/>`_ for simulation.
Ensure that it is installed and available in your system's PATH by running the ``iverilog --version`` command.
However, any supported Verilog simulator can be used for this tutorial.
See :ref:`simulator-support` for a comprehensive list of the supported simulators.

The code for the following example is available in the cocotb repository:
:reposrc:`examples/first_steps <examples/first_steps>`.

Alternatively, the files can be downloaded directly here:

    * :download:`counter.sv <../../examples/first_steps/counter.sv>`
    * :download:`counter_tests.py <../../examples/first_steps/counter_tests.py>`
    * :download:`Makefile <../../examples/first_steps/Makefile>`

If you plan to follow along with the tutorial, you must at a minimum download the design source file (:file:`counter.sv`).

The Design Under Test
---------------------

Our design is a simple 8-bit counter with a clock, enable, reset, and set input.
On every rising edge of ``clk``, in order of precedence:

* The counter resets to ``0`` if the ``rst`` signal is high.
* The counter is set to the value of ``din`` if the ``set`` signal is high.
* The counter is incremented if the ``ena`` signal is high.
* Otherwise, the counter holds its value.

.. image:: ../diagrams/counter.svg


Building your Design and Running Simulations
============================================

"cocotb" primarily refers to the Python environment and library which tests are written in,
and is mostly agnostic to how you build your design and run simulations.
However, cocotb provides a simple Makefile-based system for building and running simulations to help get users started quickly.

First create a file named ``Makefile``.
In that Makefile the following make variables must be specified:

* :make:var:`SIM`: The simulator to use.
* :make:var:`TOPLEVEL_LANG`: The language of the toplevel module or entity (``verilog`` in our case).
* :make:var:`VERILOG_SOURCES` and/or :make:var:`VHDL_SOURCES`: The design source files.
* :envvar:`COCOTB_TOPLEVEL`: The toplevel module or entity to instantiate (``counter`` in our case).
* :envvar:`COCOTB_TEST_MODULES`: The Python modules that contain our cocotb tests (the file containing the test without the `.py` extension, ``counter_tests`` in our case).
* :make:var:`WAVES` (optional): Enables waveform dumping.

Following the variable definitions is the line

.. code-block:: make

    include $(cocotb-config --makefiles)/Makefile.sim

This runs the command ``cocotb-config --makefiles`` which returns the path to the directory containing cocotb's Makefiles.
Including the file ``Makefile.sim`` defines the necessary make targets to build the design and run cocotb simulations.

Putting that together for our design looks like this:

.. literalinclude:: ../../examples/first_steps/Makefile
    :language: make
    :start-after: # Makefile


Creating a Test
===============

First, create a Python module to put your cocotb tests in.
Python modules are simply files with a ``.py`` extension.
The filename we choose does not matter as long as it is consistent with the value of :envvar:`COCOTB_TEST_MODULES` we created in the Makefile.
(For this tutorial we will use the filename :file:`counter_tests.py`).

Then, create a cocotb test in the newly created Python module by decorating a :term:`coroutine function` with :deco:`cocotb.test`.
The function must accept at least one positional argument, typically named ``dut``.
This object will be used to interact with the :term:`!DUT`.

Finally, let's make this test do something really simple, like print ``Hello, World!``.
We accomplish that using Python's :mod:`logging` system.
cocotb provides :data:`cocotb.log` for tests to use for their logging.
We will call the :meth:`cocotb.log.info() <logging.Logger.info>` method to log our message at the ``INFO`` level.

.. literalinclude:: ../../examples/first_steps/counter_tests.py
    :language: python
    :start-after: # test_hello_world
    :end-before: # end test_hello_world


Running Your Test
=================

Now that we have a Makefile to build our design and run our simulations, and at least one test defined, we can run a simulation.

Running the ``make`` command in the directory where the Makefile is located will build your design,
start a simulation,
load the cocotb environment,
and then run your cocotb tests.

.. code-block:: bash

    make

Interpreting the Output
-----------------------

You will see output from both Icarus Verilog and cocotb in the terminal.
The cocotb part of the output will look like the following:

.. code-block:: text
    :class: full-width

      -.--ns INFO     pygpi                              ..ib/pygpi/embed.cpp:113  in initialize                      Using Python 3.12.3 interpreter at /usr/bin/python3.12
      0.00ns INFO     cocotb                             Running on Icarus Verilog version 13.0 (devel)
      0.00ns INFO     cocotb                             Seeding Python random module with 1766343030
      0.00ns INFO     cocotb                             Initialized cocotb v2.0.1 from /home/user/.local/lib/python3.12/site-packages/cocotb
      0.00ns INFO     cocotb                             Running tests
      0.00ns INFO     cocotb.regression                  running counter_tests.test_hello_world (1/1)
      0.00ns INFO     test                               Hello, World!
      0.00ns INFO     cocotb.regression                  counter_tests.test_hello_world passed
      0.00ns INFO     cocotb.regression                  *****************************************************************************************
                                                         ** TEST                             STATUS  SIM TIME (ns)  REAL TIME (s)  RATIO (ns/s) **
                                                         *****************************************************************************************
                                                         ** counter_tests.test_hello_world    PASS           0.00           0.00          0.00  **
                                                         *****************************************************************************************
                                                         ** TESTS=1 PASS=1 FAIL=0 SKIP=0                     0.00           0.00          0.00  **
                                                         *****************************************************************************************

The first column of any log is the simulation time when the log message was logged.
The next column is the log level of the message, such as ``INFO``, ``WARNING``, or ``ERROR``.
The next column is the name of the logger that logged the message, such as ``cocotb`` or ``test``.
Finally, the last column is the log message itself.

The first few lines contain some information useful for debugging;
including the cocotb version, the simulator used and its version, and the Python interpreter used.
If any of these values are not what you expect them to be, your Makefile or Python environment may need to be adjusted.

.. code-block:: text
    :class: full-width

    ..ib/pygpi/embed.cpp:113  in initialize                      Using Python 3.12.3 interpreter at /usr/bin/python3.12
    Running on Icarus Verilog version 13.0 (devel)
    Seeding Python random module with 1766343030
    Initialized cocotb v2.0.1 from /home/user/.local/lib/python3.12/site-packages/cocotb

After that we see where the regression module starts ``Running tests``.
On the next line we see our ``test_hello_world`` test in our module ``counter_tests`` started running at simulation time ``0.00ns``.
We see that ``Hello, World!`` log message,
then we see a line stating that the test passed.

.. code-block:: text

    Running tests
    running counter_tests.test_hello_world (1/1)
    Hello, World!
    counter_tests.test_hello_world passed

Finally, after all (one) of our tests have run, we see a summary of all tests that were run.
Each line of the summary shows the test results, how long the simulation took in simulated time and real time,
and the ratio between the two (for performance analysis).
At the bottom of the summary is the total number of tests run, how many passed, failed, or were skipped;
as well as the total simulation time, real time, and ratio.

.. code-block:: text

    *****************************************************************************************
    ** TEST                             STATUS  SIM TIME (ns)  REAL TIME (s)  RATIO (ns/s) **
    *****************************************************************************************
    ** counter_tests.test_hello_world    PASS           0.00           0.00          0.00  **
    *****************************************************************************************
    ** TESTS=1 PASS=1 FAIL=0 SKIP=0                     0.00           0.00          0.00  **
    *****************************************************************************************

Overriding Makefile Variables
-----------------------------

``make`` allows variables to be defined on the command line, which will override any value defined in the Makefile.
For example to run the simulation with Siemens Questa and without waveform generation,
``make`` can be invoked as follows:

.. code-block:: bash

    make SIM=questa WAVES=0


cocotb Fundamentals
===================

We have a test running, now we need it to do something useful.
Before we start verifying the design lets first try to get a clock running.
Luckily, this task will introduce us to all of the fundamental features of cocotb.

Navigating the Design
---------------------

The ``dut`` object passed to the function is a Python representation of the design
starting from the module scope of our selected :make:var:`COCOTB_TOPLEVEL`.
If you are familiar with "hierarchical references" in (System)Verilog or "external names" in VHDL,
this is quite similar.

We use Python's attribute access syntax (``obj.attr``) to access named objects in a scope,
such as a signal in a module or a module instance in a generate loop.
Likewise we can use Python's item access syntax (``obj[key]``) to access objects in an array or generate loop by index.
For example, to access the clock port in our design, named ``clk``, we use ``dut.clk``.

.. literalinclude:: ../../examples/first_steps/counter_tests.py
    :language: python
    :start-after: # test_accessing
    :end-before: # end test_accessing

If we try to access an object that doesn't exist cocotb will raise an :exc:`AttributeError`.

Getting and Setting Values
--------------------------

Now we need to set the value of the clock.
We can get the current value of a signal, port, parameter, or generic by accessing its :attr:`~cocotb.handle.ValueObjectBase.value` attribute.
Similarly, we can set the value of a signal or port by assigning to its :attr:`!value` attribute.

The Python type returned when getting the value depends on the type of the HDL object being accessed.
For scalar logic signals like our clock signal, this will be :class:`.Logic`.
It behaves much like a ``logic`` value would in Verilog or ``std_logic`` in VHDL.

When setting the value a larger set of types are supported to make the code more readable.
For example, when setting a logic vector like ``din`` we can use an integer value.

.. literalinclude:: ../../examples/first_steps/counter_tests.py
    :language: python
    :start-after: # test_getting_setting_values
    :end-before: # end test_getting_setting_values

The logs above will print ``X`` at the beginning of simulation, as that is the default value for uninitialized ``logic`` signals in Verilog.
However, even if you put the logs after the write, you'll still see ``X`` as the value of the signals.
That is because cocotb writes are :term:`inertial <inertial deposit>`, much like non-blocking writes.
To see the writes take effect, we will need to wait some time.

Waiting Simulation Time
-----------------------

You may have noticed the :keyword:`async` in front of the test function definitions;
this turns the function into a :term:`coroutine`.
Coroutines are like functions, but their execution can be paused, allowing other coroutines to run, before their execution resumes.
Whenever a coroutine reaches an :keyword:`await` expression, the execution of that coroutine is paused until the thing being :keyword:`!await`\ ed finishes.

cocotb provides :term:`triggers <trigger>` which are :term:`awaitable` objects for simulator events like reaching a certain simulation time or a signal changing value.
To wait for simulation time to pass in cocotb we :keyword:`!await` a :class:`.Timer` trigger.

.. literalinclude:: ../../examples/first_steps/counter_tests.py
    :language: python
    :start-after: # test_waiting
    :end-before: # end test_waiting

Viewing the Waveforms
---------------------

Now we have enough to build a clock using cocotb.
It looks something like this:

.. literalinclude:: ../../examples/first_steps/counter_tests.py
    :language: python
    :start-after: # test_clock
    :end-before: # end test_clock

If we place this test in our test module and run a simulation, it will generate a clock.
If you've set the :envvar:`WAVES` variable in your Makefile to ``1`` (or passed ``WAVES=1`` on the command line when running make),
then a waveform file will be created.
If you are using Icarus, this will be called ``sim_build/counter.fst`` by default.
We can pull up these waveforms in any waveform viewer to see our clock running and it will look something like what's below.

.. wavedrom:: test_clock

   {
        "signal": [
            {
                "name": "counter.clk",
                "wave": "10101010101010101010",
                "data": []
            },
            {
                "name": "counter.din[7:0]",
                "wave": "=...................",
                "data": [
                    "xxxxxxxx"
                ]
            },
            {
                "name": "counter.ena",
                "wave": "x...................",
                "data": []
            },
            {
                "name": "counter.rst",
                "wave": "x...................",
                "data": []
            },
            {
                "name": "counter.set",
                "wave": "x...................",
                "data": []
            },
            {
                "name": "counter.count[7:0]",
                "wave": "x...................",
                "data": []
            }
        ],
        "config": {
            "hscale": 1
        }
    }


Concurrency
-----------

While that test is great and all, running the clock in the main test prevents us from doing anything else!
So let's run that clock in a :term:`Task <task>` `concurrent` to the main test coroutine.
This means that the clock will be running independently "at the same time" as the main test coroutine, freeing up our test coroutine to do other things.

.. note::
    "At the same time" does not mean the coroutines are running in parallel.
    Only one :term:`!task` is running while all the others are paused.
    Once it is blocked by awaiting a :term:`!trigger` a different :term:`!task` is resumed.
    This prevents any concerns of race conditions or a need to guard critical sections.

cocotb provides the :func:`cocotb.start_soon` function to run a coroutine as a concurrent :term:`!task`.

.. literalinclude:: ../../examples/first_steps/counter_tests.py
    :language: python
    :start-after: # test_clock_concurrent
    :end-before: # end test_clock_concurrent

The first thing you may notice is that we have another :keyword:`!async` function, ``run_clock``.
This is a :term:`coroutine function` that contains the logic for implementing the clock.
We can make as many of these helper coroutine functions as we want to break up our code into more manageable pieces.
And in doing so we can start to design for reuse.

You may also notice that the ``run_clock`` coroutine was changed to be an indefinite loop.
This does not prevent the test from finishing;
as soon as the main test coroutine finishes, all other :class:`!Task`\ s are cancelled and the test ends.

While writing your own clock is fun,
cocotb provides :class:`~cocotb.clock.Clock` which is a reusable and configurable clock component to do the same thing.
It's implemented in C++ when possible to achieve better performance.
We will be using that for the following examples.

Waiting for Values to Change
----------------------------

Another common :term:`!trigger` is the value change trigger.
We will need this to finish our basic verification.

cocotb provides the following value change triggers:

- :class:`~cocotb.triggers.RisingEdge`: Blocks the coroutine until the given signal changes from any non-\ ``1`` value to a ``1`` value.
- :class:`~cocotb.triggers.FallingEdge`: Blocks the coroutine until the given signal changes from any non-\ ``0`` value to a ``0`` value.
- :class:`~cocotb.triggers.ValueChange`: Blocks the coroutine until any value change is seen on the given signal.

It is customary to use the rising edge of the clock to drive registered signals, so we will be using that in the below examples.

.. literalinclude:: ../../examples/first_steps/counter_tests.py
    :language: python
    :start-after: # test_edge_trigger
    :end-before: # end test_edge_trigger

We created the ``reset`` coroutine function for our reusable reset logic.
Not only can we :func:`!cocotb.start_soon` coroutine functions to run them concurrently,
but we can also :keyword:`!await` on them which will block the caller until the reset coroutine finishes.

If we run the test and pull up the waveforms, we will see our initial value of ``10`` be loaded into the counter,
and then the counter increments from there on every rising edge of the clock for the next 20 cycles.

.. wavedrom:: test_edge_trigger

    {
        "signal": [
            {
                "name": "counter.clk",
                "wave": "10101010101010101010",
                "data": []
            },
            {
                "name": "counter.din[7:0]",
                "wave": "=...=...............",
                "data": [
                    "0",
                    "10"
                ]
            },
            {
                "name": "counter.ena",
                "wave": "0.....1.............",
                "data": []
            },
            {
                "name": "counter.rst",
                "wave": "1...0...............",
                "data": []
            },
            {
                "name": "counter.set",
                "wave": "0...1.0.............",
                "data": []
            },
            {
                "name": "counter.count[7:0]",
                "wave": "=.....=.=.=.=.=.=.=.",
                "data": [
                    "0",
                    "10",
                    "11",
                    "12",
                    "13",
                    "14",
                    "15",
                    "16",
                ]
            }
        ],
        "config": {
            "hscale": 1
        }
    }


Self-Checking Tests
-------------------

Again, that's great and all, but verifying a design by staring at waveforms is very sub-optimal.
We want to write tests that can automatically check the design for the behavior we expect and fail if it does not match our expectations.
cocotb accomplishes this using Python's built-in :keyword:`assert` statement.

.. literalinclude:: ../../examples/first_steps/counter_tests.py
    :language: python
    :start-after: # test_self_checking
    :end-before: # end test_self_checking

One thing you may notice in the above example is that after each ``await RisingEdge(dut.clk)`` we also ``await Timer(1, 'ns')`` before sampling register values.
This is because :class:`!RisingEdge` and the other value change triggers leave you directly after the signal changes value,
but before any HDL processes sensitive to that signal have run.
This means that if you get the value of ``dut.count`` immediately following a ``RisingEdge(dut.clk)`` it will be the value at the end of last time step.
If you wish to sample the value after all HDL processes have *quiesced*, you have to wait some time.
It's common in SystemVerilog to set input delays on clocking blocks to a small amount of time, such as 1 ns, so we've chosen to do the same here.

Failing Tests
-------------

Now we've written a test which works, but what happens when the test fails?
The critical flaw in our current checking is that we are not handling the case where the counter wraps around back to ``0`` after reaching its maximum value of ``255``.
So if we modify the previous example to load ``250`` as the initial counter value and re-run the test, we should see a failure after a few clock cycles.

.. code-block:: text
    :class: full-width

     0.00ns INFO     cocotb.regression                  running counter_tests.test_self_checking (1/1)
    91.00ns WARNING  cocotb.regression                  counter_tests.test_self_checking failed
                                                        Traceback (most recent call last):
                                                          File "cocotb/examples/first_steps/counter_tests.py", line 53, in test_self_checking
                                                            assert dut.count.value == expected_value
                                                        AssertionError: assert LogicArray('00000000', Range(7, 'downto', 0)) == 256
                                                         +  where LogicArray('00000000', Range(7, 'downto', 0)) = PackedObject(counter.count).value
                                                         +    where PackedObject(counter.count) = HierarchyObject(counter).count
    91.00ns INFO     cocotb.regression                  ******************************************************************************************
                                                        ** TEST                              STATUS  SIM TIME (ns)  REAL TIME (s)  RATIO (ns/s) **
                                                        ******************************************************************************************
                                                        ** counter_tests.test_self_checking   FAIL          91.00           0.00      30371.74  **
                                                        ******************************************************************************************
                                                        ** TESTS=1 PASS=0 FAIL=1 SKIP=0                     91.00           0.02       5579.24  **
                                                        ******************************************************************************************

Just as anticipated, ``dut.count.value`` wrapped back around to ``0``, while the model incremented ``expected_value`` naively to ``256``.
This causes the ``assert dut.count.value == expected_value`` statement to fail ending the test.

Looking at the output we can see a bit more detail about the failure.
We get a traceback of the failure, showing the line that failed, and all the line numbers of every function call on the stack.
It shows the :keyword:`!assert` line that failed, what the values each side of the match was, and a breakdown of how those values were derived.

Next Steps
==========

Now that we have the fundamentals down, you can start to explore more advanced features of cocotb.
There are more detailed tutorials on everything covered here in the ``Tutorials`` section of the documentation,
several examples in the ``Examples`` section of the documentation,
and a comprehensive API reference in the ``Reference`` section.
