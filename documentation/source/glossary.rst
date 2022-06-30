.. _glossary:

Glossary
========

.. glossary::

   BFM
      Bus Functional Model

   coroutine function
      The definition of a function that, when called, returns a coroutine object.
      Implemented using :keyword:`async` functions.
      See also the :term:`Python glossary <python:coroutine function>`.

   coroutine
      The result of calling a :term:`coroutine function`.
      Coroutines are not run immediately, you must either
      :keyword:`await` on them which blocks the awaiting coroutine until it is finished;
      or fork the coroutine, turning it into a :term:`task`, which runs concurrently.
      See also the :term:`Python glossary <python:coroutine>`.

   DUT
      Design under Test

   DUV
      Design under Verification

   FLI
      Foreign Language Interface. Mentor Graphics' equivalent to :term:`VHPI`

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

   task
      The result of forking a :term:`coroutine`. A task represents a concurrently running coroutine.

   UVM
      Universal Verification Methodology

   VHPI
      The VHDL Procedural Interface, an application-programming interface to VHDL tools.

   VIP
      Verification IP

   VPI
      The Verilog Procedural Interface, an application-programming interface to (System)Verilog tools.
      Its original name was "PLI 2.0".

..
   Driver
      TBD

   Monitor
      TBD

   Scoreboard
      TBD
