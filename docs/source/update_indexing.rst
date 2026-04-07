.. _update-indexing:

******************************
Update Indexing for cocotb 2.0
******************************

cocotb 2.0 changes what types are returned when getting a value from a
:ref:`Logic-like <logic-handle-value-changes>` or :ref:`Array-like <array-handle-value-changes>` simulator object.
This can require a change to the testbench code in how those values are indexed.
Because this change breaks backwards compatibility silently,
this document and the following set of features were added to assist users in updating the indexing in their existing tests built against cocotb 1.x.

.. autoclass:: cocotb.types.IndexingChangedWarning

.. envvar:: COCOTB_INDEXING_CHANGED_WARNING

    Set this environment variable to ``1`` to cause a warning to be emitted on all :class:`.LogicArray` and :class:`.Array` indexing and slicing operations
    if the indexing would have changed between cocotb 1.x and 2.x.

How to Find Indexing Changes
============================

Set the :envvar:`!COCOTB_INDEXING_CHANGED_WARNING` environment variable to ``1`` and run your test.
You should see warnings emitted on every line of your testbench that indices or slices a :class:`.LogicArray` or :class:`.Array` where the indexing has changed.
The warning will tell you what index you used and what the new index should be.

.. code-block:: console

    $ export COCOTB_INDEXING_CHANGED_WARNING=1
    $ make
    ...
    /home/user/project/tests/unit_tests.py:160: IndexingChangedWarning: Index 0 is now 7
      left_bit = dut.signal.value[0]
    ...
    /home/user/project/tests/unit_tests.py:543: IndexingChangedWarning: Index 0 is now 3
      if handle.value[i]:
    /home/user/project/tests/unit_tests.py:543: IndexingChangedWarning: Index 1 is now 2
      if handle.value[i]:
    /home/user/project/tests/unit_tests.py:543: IndexingChangedWarning: Index 2 is now 1
      if handle.value[i]:
    /home/user/project/tests/unit_tests.py:543: IndexingChangedWarning: Index 3 is now 0
      if handle.value[i]:
    ...
    /home/user/project/tests/unit_tests.py:232: IndexingChangedWarning: Slice 0:3 is now 7:4
      field = dut.signal.value[:3]


How to Update Indexing
======================

For static indices or slices, simply change the index or slice to the new value.

.. code-block:: verilog
    :caption: Signal definition

    logic [3:0] signal;
    logic [3:0] array [1:4];

.. code-block:: python
    :caption: Old 0-based indexing
    :class: removed

    dut.signal.value = "1010"
    ...
    assert dut.signal.value[0] == 1  # index 0 is always left-most

    dut.array.value = [100, 101, 102, 103]
    ...
    assert dut.array.value[0] == 100  # index 0 is always left-most

.. code-block:: python
    :caption: New HDL-based indexing (packed object / logic array)
    :class: new

    dut.signal.value = "1010"
    ...
    assert dut.signal.value[3] == 1  # index 3 is now the left-most

    dut.array.value = [100, 101, 102, 103]
    ...
    assert dut.array.value[1] == 100  # index 1 is now the left-most

.. note::

    If you previously used the static indices ``0`` or ``-1`` to refer to the first or last element in an array,
    ``array[array.left]`` or ``array[array.right]``, respectively, may be a better spelling.

When dealing with loops involving indices, there are several options, depending on your needs.
If you are looping over the indices to then index each element, you can instead iterate over the array directly.
This can be combined with :func:`enumerate` to get the ``0``-based index of each element, if needed.

.. code-block:: python
    :caption: Looping over indices
    :class: removed

    for i in range(len(dut.signal.value)):
        bit = dut.signal.value[i]
        ...

.. code-block:: python
    :caption: Looping over elements directly
    :class: new

    for i, bit in enumerate(dut.signal.value):
        ...

If you need to use the index value, you can loop over the ``array.range`` object to get the indices in left-to-right order.

.. code-block:: verilog
    :caption: HDL signal being used

    // Two arrays using the same indices
    logic [3:0] array [1:4];
    logic [4:0] doubled_array [1:4];

.. code-block:: python
    :caption: Looping over indices
    :class: removed

    for i in range(len(dut.array.value)):  # 0, 1, 2, 3
        dut.doubled_array[i].value = 2 * dut.array.value[i]

.. code-block:: python
    :caption: Looping over ``range``
    :class: new

    array_value = dut.array.value
    for i in array_value.range:  # 1, 2, 3, 4
        dut.doubled_array[i].value = 2 * array_value[i]


You can also use the ``array.range`` object to translate ``0`` to ``len()-1`` indexing to the one used by :class:`!LogicArray` and :class:`!Array`.
Use this as a last resort, as it is less readable and has runtime overhead compared to the other options.

.. code-block:: python
    :class: new

    val = LogicArray("1010", Range(3, 0))
    assert val[0] == 0      # index 0 is right-most
    ind = val.range[0]      # 0th range value is 3
    assert val[ind] == "1"  # index 3 is left-most


Gradual Update
==============

The recommended approach is to update one module at a time.
This is done by using the :envvar:`PYTHONWARNINGS` environment variable to limit which modules can emit an :class:`!IndexingChangedWarning`.
The :envvar:`!PYTHONWARNINGS` value below will ignore all :class:`!IndexingChangedWarning` except those from the ``unit_tests`` module.

.. code-block:: console

    $ export PYTHONWARNINGS=ignore::cocotb.types.IndexingChangedWarning,default::cocotb.types.IndexingChangedWarning:unit_tests
    $ export COCOTB_INDEXING_CHANGED_WARNING=1
    $ make

After eliminating all warnings from one module, update the :envvar:`!PYTHONWARNINGS` environment variable to the next module and repeat until all modules are updated.
Then rerun all tests with :envvar:`!PYTHONWARNINGS` unset to ensure all warnings are gone.
