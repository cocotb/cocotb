.. _best_practices:

**************
Best Practices
**************

.. _performance:

Performance Considerations
==========================

In order to get the maximum performance out of a cocotb testbench,
the following points may help you.


Clock Generator in HDL
----------------------

Generate your clock with a HDL module instead of using :class:`~cocotb.clock.Clock`.
Doing so prevents calls back into Python every single clock half-period.

Performance Impact: **Major**


Reusing Objects
---------------

Do not create single-use objects in a loop but instead create them outside the loop and reuse them.
Typical cases are :class:`~cocotb.triggers.Timer` or :class:`~cocotb.triggers.RisingEdge` of the clock signal,
as shown below:

.. list-table::

   * - .. code-block:: python
          :caption: Inefficient ``Timer`` object re-creation

          while True:
              await Timer(0.5, "ns")
              signal <= ~signal.value

     - .. code-block:: python
          :caption: More efficient ``Timer`` object re-use

          halfperiod = Timer(0.5, "ns")
          while True:
              await halfperiod
              signal <= ~signal.value

This is because creating an object has a small additional overhead compared to using an existing object.

Performance Impact: Minor
