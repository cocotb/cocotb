##############
Best Practices
##############

This example is available in the repo at :reposrc:`examples/matrix_multiplier <examples/matrix_multiplier>`.
It is designed to show best practices for writing cocotb testbenches.
Notably, it:

* Creates reusable components such as Monitors and Checkers
* Separates stimulus and analysis into independent tasks/components
* Uses a pure Python model to compute expected results
* Stimulates the design using randomized data

The Design
==========

The design is a simple matrix multiplier.
It is implemented in both **VHDL** and **SystemVerilog** to accommodate users of both languages and all supported simulators.
Only one design is run at a time.

The design takes two matrices ``a_i`` and ``b_i`` as inputs
and provides the resulting matrix ``c_o`` as an output.
On each rising clock edge,
``c_o`` is calculated and output.
When input ``valid_i`` is high
and ``c_o`` is calculated,
``valid_o`` goes high to signal a valid output value.

The number of data bits for each entry in the matrices,
as well as the row and column counts for each matrix,
are configurable in the Makefile.

The Testbench Components
========================

Monitors
--------

The :class:`!DataValidMonitor` is a reusable monitor that monitors a streaming data/valid bus and emits transactions.
Transactions are pushed out via a callback function.
A callback function was used so that the downstream can react immediately *or* queue the transactions for later processing.
Pushing the transaction into a queue removes the ability for the downstream to react immediately.

Drivers
-------

We use cocotb's :class:`~cocotb.clock.Clock` driver class to drive the clock signal of the design.

The :class:`!DataValidDriver` is a reusable driver that drives a streaming data/valid bus with data.
The :meth:`!send` method pushes data into the Driver and returns an awaitable object which allows the caller to wait until the data has been applied to the interface.
This approach was selected so that the caller can decide to either wait for the send to complete or push data to the driver without waiting.

The :meth:`!send` method pushes the data into a :class:`!Mailbox` instead of directly applying it to the interface.
This allows the driver to control the timing of the data and valid signals without being interrupted by, or depending upon, the timing of the user.

Reference Model
---------------

A pure Python model of the design, :class:`!MatrixMultiplierModel`, is implemented to compute expected results.
Writing this in pure Python without using any cocotb features allows it to be reused in other contexts, such as software unit tests.

Analysis
--------

The :class:`!InOrderChecker` is a reusable checker that compares the output of the design to the expected results in the order they are received.
It has a configurable comparison function to allow for flexible checking of the results.
Mismatches are logged and recorded, but only cause the test to end immediately if the ``fail_on_error`` flag is set.
This gives the user the ability to see all the errors that occurred during the test instead of just the first one.

The checker assumes that the expected results will arrive before the corresponding actual outputs.
This allows the checker to fail if the design produces output when it wasn't expected to.
Because the monitor pushes transactions out immediately, and the model is in pure Python without any time modeling,
we can expect the expected results to be available before the design produces its output.

Testbench Top
-------------

Tying this all together is the :class:`!MatrixMultiplierTestbench` class.
It contains the :class:`!Clock` driver and a :meth:`reset` method to reset the design.
It instantiates a :class:`!DataValidDriver` for the write interface,
:class:`!DataValidMonitor`\ s for the write and read interface,
then hooks the input monitor up to a :class:`!MatrixMultiplierModel` to compute expected results,
and hooks the expected results from the model and the actual results from the output monitor up to an :class:`!InOrderChecker` to compare the results.

Stimulus Generation
===================

The main test coroutine generates random stimulus which is sent to the testbench's :attr:`!input_drv`.
Between each send, it waits a random number of clock cycles to provide more varied timing of the stimulus.
This could also be accomplished with a `Sequencer` which is connected to the driver,
and a `Sequence` generator which generates the random stimulus and timing information for the sequencer to execute,
but the current approach was chosen for simplicity.

Test Execution Flow
===================

All components in the testbench have a :meth:`!start` and a :meth:`!stop` method to control when they are active.
The :class:`!MatrixMultiplierTestbench` has these functions which call out the corresponding functions of the components in the correct order.
This allows the testbench to control when the components are active and ensures that they are started and stopped in the correct order.

After we start the testbench, we run the testbench's :meth:`!reset` method to reset the design.
Then we run the main test sequence driving the stimulus into the DUT, while the analysis concurrently checks the results.
Once all the test inputs have been applied, the test waits a small amount of time for the design to quiesce
and allow any errant transactions to flow into the checker causing a failure.
Then it checks that the checker has not seen any errors before ending.
