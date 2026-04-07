.. _glossary:

Glossary
========

.. glossary::
   :sorted:

   BFM
      Bus Functional Model

   blocking function
      A function that blocks the caller until the function finishes.
      This is typically a regular function,
      but sometimes involves calls to threaded code which blocks execution for an indeterminate amount of time.
      See also the :term:`Python glossary <python:function>`.

   coroutine function
      The definition of a function that, when called, returns a coroutine object.
      Implemented using :keyword:`async` functions.
      See also the :term:`Python glossary <python:coroutine function>`.

   coroutine
      The result of calling a :term:`coroutine function`.
      Coroutines are not run immediately, you must either
      :keyword:`await` on them which blocks the awaiting coroutine until it is finished;
      or turn them into a :term:`task`, which can be run concurrently.
      See also the :term:`Python glossary <python:coroutine>`.

   task
      A :term:`coroutine` that can be run concurrently to other tasks.

   trigger
      An :term:`awaitable` object which when :keyword:`awaited <await>` will block the current :term:`task` until its condition is met.
      For example, a :class:`RisingEdge(dut.clk) <cocotb.triggers.RisingEdge>` trigger will block until the next rising edge of the ``dut.clk`` signal.

   DUT
      Design under Test

   DUV
      Design under Verification

   FLI
      Foreign Language Interface. Mentor Graphics' equivalent to :term:`VHPI`.

   GPI
      Generic Procedural Interface, cocotb's abstraction over :term:`VPI`, :term:`VHPI`, and :term:`FLI`.

   HAL
      Hardware Abstraction Layer

   HDL
      Hardware Description Language

   MDV
      Metric-driven Verification

   RTL
      Register Transfer Level

   UVM
      Universal Verification Methodology

   VHPI
      The VHDL Procedural Interface, an application-programming interface to VHDL tools.

   VIP
      Verification IP

   VPI
      The Verilog Procedural Interface, an application-programming interface to (System)Verilog tools.
      Its original name was "PLI 2.0".

   time step
      A single point in simulated time, comprised of a series of one or more :term:`evaluation cycles <evaluation cycle>`.

   evaluation cycle
      One iteration of the evaluation loop in a :term:`time step`.
      Occurs when HDL or cocotb code is executed in reaction to events, such as simulated time advancing or signal or variable values changing.
      The executed code tends to create more events, leading to the next evaluation cycle.

   inertial deposit
      :term:`Depositing <deposit>` a value on a signal or variable at the end of the current delta cycle.

   no-delay deposit
      :term:`Depositing <deposit>` a value on a signal or variable immediately.

   driving
      Continuously :term:`depositing <deposit>` a value to a signal. cocotb cannot drive signals, only deposit or force values.

   deposit
      Setting the value of a signal or variable once. May be :term:`inertial <inertial deposit>` or :term:`no-delay <no-delay deposit>`.

   force
      Setting the value to a signal or variable once immediately, then locking it so the value can't change.

   release
      Setting the value to a signal or variable once immediately, then unlocking it from a previous :term:`force`.

   simulator object
      An addressable object from the :term:`DUT`. Corresponds to a signal, variable, or hierarchical element in the :term:`HDL` code.
