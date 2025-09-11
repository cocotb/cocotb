=======================
Upgrading to cocotb 2.0
=======================

cocotb 2.0 makes testbenches easier to understand and write.
Some of these improvements require updates to existing testbenches.
This guide helps you port existing testbenches to cocotb 2.0.

**************************
Step-by-step to cocotb 2.0
**************************

The migration to cocotb 2.0 is a two-step process.
The first step is a gradual migration that can be performed in small increments as time permits and keeps the testbench fully operational.
The second step is a flag-day migration to switch outdated APIs to their new counterparts.

Step 1: Upgrade to cocotb 1.9 and resolve all deprecation warnings
==================================================================

Many of the new features in cocotb 2.0 were already introduced in cocotb 1.x, while keeping existing functionality in place.
Deprecation warnings highlight where functionality is used that will be gone in cocotb 2.0.
Resolving all deprecations is therefore the first step in upgrading.

1. Upgrade to the latest version of cocotb 1.9.
2. Resolve all deprecation warnings.

With every warning resolved, your code will be better prepared for cocotb 2.0.

Step 2: Move to cocotb 2.0
==========================

After step 1 your testbenches are ready for the final migration to cocotb 2.0.

1. Start from a known-good state.
   Ensure all tests are passing, the logic is stable, and all code is committed.
2. Upgrade to cocotb 2.0.
3. Run the testbench to see where it fails.
   Replace outdated constructs as needed.
   Rinse and repeat.
4. Your testbenches are now running on cocotb 2.0!

Continue reading on this page for common migration steps.
Also have a look at the :doc:`release_notes` for cocotb 2.0 and the linked GitHub pull requests or issues, which often also include changes to the cocotb tests that show the before and after of a change.

You might see some new deprecation warnings in your code after the upgrade.
As in step one, address those at your convenience (the sooner the better, of course).

If you get lost or have questions, :doc:`reach out through one of our support channels <support>`, we're happy to help!


**************************************************************
Use :func:`!cocotb.start_soon` instead of :func:`!cocotb.fork`
**************************************************************

Change
======

:external+cocotb19:py:func:`cocotb.fork` was removed and replaced with :func:`cocotb.start_soon`.

How to Upgrade
==============

* Replace all instances of :func:`!cocotb.fork` with :func:`!cocotb.start_soon`.
* Run tests to check for any changes in behavior.

.. code-block:: python
    :caption: Old way with :func:`!cocotb.fork`
    :class: removed

    task = cocotb.fork(drive_clk())

.. code-block:: python
    :caption: New way with :func:`!cocotb.start_soon`
    :class: new

    task = cocotb.start_soon(drive_clk())

Rationale
=========

:func:`!cocotb.fork` would turn :term:`coroutine`\s into :class:`~cocotb.task.Task`\s that would run concurrently to the current :term:`task`.
However, it would immediately run the coroutine until the first :keyword:`await` was seen.
This made the scheduler re-entrant and caused a series of hard to diagnose bugs
and required extra state/sanity checking leading to runtime overhead.
For these reasons :func:`!cocotb.fork` was deprecated in cocotb 1.7 and replaced with :func:`!cocotb.start_soon`.
:func:`!cocotb.start_soon` does not start the coroutine immediately, but rather "soon",
preventing scheduler re-entrancy and sidestepping an entire class of bugs and runtime overhead.

`The cocotb blog post on this change <https://fossi-foundation.org/blog/2021-10-20-cocotb-1-6-0>`_
is very illustrative of how :func:`!cocotb.start_soon` and :func:`!cocotb.fork` are different.

Additional Details
==================

Coroutines run immediately
--------------------------

There is a slight change in behavior due to :func:`!cocotb.start_soon` not running the given coroutine immediately.
This will not matter in most cases, but cases where it does matter are difficult to spot.

If you have a coroutine (the parent) which :func:`!cocotb.fork`\ s another coroutine (the child)
and expects the child coroutine to run to a point before allowing the parent to continue running,
you will have to add additional code to ensure that happens.

In general, the easiest way to fix this is to add an :class:`await NullTrigger() <cocotb.triggers.NullTrigger>` after the call to :func:`!cocotb.start_soon`.

.. code-block:: python
    :caption: Set up example...

    async def hello_world():
        cocotb.log.info("Hello, world!")

.. code-block:: python
    :caption: Behavior of the old :func:`!cocotb.fork`
    :class: removed

    cocotb.fork(hello_world())
    # "Hello, world!"

.. code-block:: python
    :caption: Behavior of the new :func:`!cocotb.start_soon`
    :class: new

    cocotb.start_soon(hello_world())
    # No print...
    await NullTrigger()
    # "Hello, world!"

One caveat of this approach is that :class:`!NullTrigger` also allows every other scheduled coroutine to run as well.
But this should generally not be an issue.

If you require the "runs immediately" behavior of :func:`!cocotb.fork`,
but are not calling it from a :term:`coroutine function`,
update the function to be a coroutine function and add an ``await NullTrigger``, if possible.
Otherwise, more serious refactorings will be necessary.


Exceptions before the first :keyword:`!await`
---------------------------------------------

Also worth noting is that with :func:`!cocotb.fork`, if there was an exception before the first :keyword:`!await`,
that exception would be thrown back to the caller of :func:`!cocotb.fork` and the ``Task`` object would not be successfully constructed.

.. code-block:: python
    :caption: Set up example...

    async def has_exception():
        if variable_does_not_exist:  # throws NameError
            await Timer(1, 'ns')

.. code-block:: python
    :caption: Behavior of the old :func:`!cocotb.fork`
    :class: removed

    try:
        task = cocotb.fork(has_exception())  # NameError comes out here
    except NameError:
        cocotb.log.info("Got expected NameError!")
    # no task object exists

.. code-block:: python
    :caption: Behavior of the new :func:`!cocotb.start_soon`
    :class: new

    task = cocotb.start_soon(has_exception())
    # no exception here
    try:
        await task  # NameError comes out here
    except NameError:
        cocotb.log.info("Got expected NameError!")


****************************************
Move away from :deco:`!cocotb.coroutine`
****************************************

Change
======

Support for generator-based coroutines using the :external+cocotb19:py:class:`@cocotb.coroutine <cocotb.coroutine>` decorator
with Python :term:`generator functions <generator>` was removed.

How to Upgrade
==============

* Remove the :deco:`!cocotb.coroutine` decorator.
* Add :keyword:`async` keyword directly before the :keyword:`def` keyword in the function definition.
* Replace any ``yield [triggers, ...]`` with :class:`await First(triggers, ...) <cocotb.triggers.First>`.
* Replace all ``yield``\ s in the function with :keyword:`await`\ s.
* Remove all imports of the :deco:`!cocotb.coroutine` decorator

.. code-block:: python
    :caption: Old way with :deco:`!cocotb.coroutine`
    :class: removed

    @cocotb.coroutine
    def my_driver():
        yield [RisingEdge(dut.clk), FallingEdge(dut.areset_n)]
        yield Timer(random.randint(10), 'ns')

.. code-block:: python
    :caption: New way with :keyword:`!async`\ /:keyword:`!await`
    :class: new

    async def my_driver():  # async instead of @cocotb.coroutine
        await First(RisingEdge(dut.clk), FallingEdge(dut.areset_n))  # await First() instead of yield [...]
        await Timer(random.randint(10), 'ns')  # await instead of yield

Rationale
=========

These existed to support defining coroutines in Python 2 and early versions of Python 3 before :term:`coroutine functions <coroutine function>`
using the :keyword:`!async`\ /:keyword:`!await` syntax was added in Python 3.5.
We no longer support versions of Python that don't support :keyword:`!async`\ /:keyword:`!await`.
Python coroutines are noticeably faster than :deco:`!cocotb.coroutine`'s implementation,
and the behavior of :deco:`!cocotb.coroutine` would have had to be changed to support changes to the scheduler.
For all those reasons the :deco:`!cocotb.coroutine` decorator and generator-based coroutine support was removed.


.. _logic-array-over-binary-value:

*********************************************************
Use :class:`!LogicArray` instead of :class:`!BinaryValue`
*********************************************************

Change
======

:external+cocotb19:py:class:`~cocotb.binary.BinaryValue` and :external+cocotb19:py:class:`~cocotb.binary.BinaryRepresentation` were removed
and replaced with the existing :class:`.Logic` and :class:`.LogicArray`.


How to Upgrade
==============

Change all constructions of :class:`!BinaryValue` to :class:`!LogicArray`.

Replace construction from :class:`int` with :meth:`.LogicArray.from_unsigned` or :meth:`.LogicArray.from_signed`.

Replace construction from :class:`bytes` with :meth:`.LogicArray.from_bytes` and pass the appropriate ``byteorder`` argument.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    BinaryValue(10, 10)
    BinaryValue("1010", n_bits=4)
    BinaryValue(-10, 8, binaryRepresentation=BinaryRepresentation.SIGNED)
    BinaryValue(b"1234", bigEndian=True)

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    LogicArray.from_unsigned(10, 10)
    LogicArray("1010")
    LogicArray.from_signed(-10, 8)
    BinaryValue.from_bytes(b"1234", byteorder="big")

----

Replace usage of :external+cocotb19:py:attr:`BinaryValue.integer <cocotb.binary.BinaryValue.integer>` and
:external+cocotb19:py:attr:`BinaryValue.signed_integer <cocotb.binary.BinaryValue.signed_integer>`
with :meth:`.LogicArray.to_unsigned` or :meth:`.LogicArray.to_signed`, respectively.

Replace usage of :external+cocotb19:py:attr:`BinaryValue.binstr <cocotb.binary.BinaryValue.binstr>`
with the :class:`str` cast (this works with :class:`!BinaryValue` as well).

Replace conversion to :class:`!bytes` with :meth:`.LogicArray.to_bytes` and pass the appropriate ``byteorder`` argument.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    val = BinaryValue(10, 4)
    assert val.integer == 10
    assert val.signed_integer == -6
    assert val.binstr == "1010"
    assert val.buff == b"\x0a"

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    val = LogicArray(10, 4)
    assert val.to_unsigned() == 10
    assert val.to_signed() == -6
    assert str(val) == "1010"
    assert val.to_bytes(byteorder="big") == b"\x0a"

----

Remove setting of the :attr:`!BinaryValue.big_endian` attribute to change endianness.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    val = BinaryValue(b"12", bigEndian=True)
    assert val.buff == b"12"
    val.big_endian = False
    assert val.buff == b"21"

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    val = LogicArray.from_bytes(b"12", byteorder="big")
    assert val.to_bytes(byteorder="big") == b"12"
    assert val.to_bytes(byteorder="little") == b"21"

----

Convert all objects to an unsigned :class:`!int` before doing any arithmetic operation,
such as ``+``, ``-``, ``/``, ``//``, ``%``, ``**``, ``- (unary)``, ``+ (unary)``, ``abs(value)``, ``>>``, or ``<<``.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    val = BinaryValue(12, 8)
    assert 8 * val == 96
    assert val << 2 == 48
    assert val / 6 == 2.0
    assert -val == -12
    # inplace modification
    val *= 3
    assert val == 36

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    val = LogicArray(12, 8)
    val_int = b.to_unsigned()
    assert 8 * val_int == 96
    assert val_int << 2 == 48
    assert val_int / 6 == 2.0
    assert -val_int == -12
    # inplace modification
    val[:] = val_int * 3
    assert val == 36

----

Change bit indexing and slicing to use the indexing provided by the ``range`` argument to the constructor.

.. note::
    Passing an :class:`!int` as the ``range`` argument will default the range to :class:`Range(range-1, "downto", 0) <cocotb.types.Range>`.
    This means index ``0`` will be the rightmost bit and not the leftmost bit like in :class:`BinaryValue`.
    Pass ``Range(0, range-1)`` when constructing :class:`!LogicArray` to retain the old indexing scheme, or update the indexing and slicing usage.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    val = BinaryValue(10, 4)
    assert val[0] == 1
    assert val[3] == 0

.. code-block:: python
    :caption: New way with :class:`!LogicArray`, specifying an ascending range
    :class: new

    val = LogicArray(10, Range(0, 3))
    assert val[0] == 1
    assert val[3] == 0

.. code-block:: python
    :caption: New way with :class:`!LogicArray`, changing indexing
    :class: new

    val = LogicArray(10, 4)
    assert val[3] == 1
    assert val[0] == 0

See :ref:`update-indexing` for more details on how to update indexing and slicing.

----

Change all uses of the :attr:`.LogicArray.binstr`, :attr:`.LogicArray.integer`, :attr:`.LogicArray.signed_integer`, and :attr:`.LogicArray.buff` setters,
as well as calls to :external+cocotb19:py:meth:`BinaryValue.assign() <cocotb.binary.BinaryValue.assign>`, to use :class:`!LogicArray`'s setitem syntax.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    val = BinaryValue(10, 8)
    val.binstr = "00001111"
    val.integer = 0b11
    val.signed_integer = -123
    val.buff = b"a"

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    val = LogicArray(10, 8)
    val[:] = "00001111"
    val[:] = LogicArray.from_unsigned(3, 8)
    # or
    val[:] = 0b00000011
    val[:] = LogicArray.from_signed(-123, 8)
    val[:] = LogicArray.from_bytes(b"a", byteorder="big")

.. note::
    Alternatively, don't modify the whole value in place, but instead modify the variable with a new value.

----

Change expected type of single indexes to :class:`.Logic` and slices to :class:`.LogicArray`.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    val = BinaryValue(10, 4)
    assert isinstance(val[0], BinaryValue)
    assert isinstance(val[0:3], BinaryValue)

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    val = LogicArray(10, 4)
    assert isinstance(val[0], Logic)
    assert isinstance(val[0:3], LogicArray)

.. note::
    :class:`Logic` supports usage in conditional expressions (e.g. ``if val: ...``),
    equality with :class:`!str`, :class:`!bool`, or :class:`!int`,
    and casting to :class:`!str`, :class:`!bool`, or :class:`!int`;
    so many behaviors overlap with :class:`!LogicArray`
    or how these values would be used previously with :class:`!BinaryValue`.

.. note::
    This also implies a change to type annotations.

Rationale
=========

In many cases :class:`!BinaryValue` would behave in unexpected ways that were often reported as errors.
These unexpected behaviors were either an unfortunate product of its design or done purposefully.
They could not necessarily be "fixed" and any fix would invariably break the API.
So rather than attempt to fix it, it was outright replaced.
Unfortunately, a gradual change is not possible with such core functionality,
so it was replaced in one step.


Additional Details
==================

There are some behaviors of :class:`!BinaryValue` that are *not* supported anymore.
They were deliberately not added to :class:`!LogicArray` because they were unnecessary, unintuitive, or had bugs.


Dynamic-sized :class:`!BinaryValue`\ s
--------------------------------------

The above examples all pass the ``n_bits`` argument to the :class:`!BinaryValue` constructor.
However, it is possible to construct a :class:`!BinaryValue` without a set size.
Doing so would allow the size of the :class:`!BinaryValue` to change whenever the value was set.

:class:`!LogicArray`\ s are fixed size.
Instead of modifying the :class:`!LogicArray` in-place with a different sized value,
modify the variable holding the :class:`!LogicArray` to point to a different value.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    val = BinaryValue(0, binaryRepresentation=BinaryRepresentation.TWOS_COMPLEMENT)
    assert len(val) == 0
    val.binstr = "1100"
    assert len(val) == 4
    val.integer = 100
    assert len(val) == 8  # minimum size in two's complement representation

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    val = LogicArray(0, 0)  # must provide size!
    assert len(val) == 0
    val = LogicArray("1100")
    assert len(val) == 4
    val = LogicArray.from_signed(100, 8)  # must provide size!
    assert len(val) == 8


Assigning with partial values and "bit-endianness"
--------------------------------------------------

Previously, when modifying a :class:`!BinaryValue` in-place using :external+cocotb19:py:meth:`BinaryValue.assign <cocotb.binary.BinaryValue.assign>`
or the :external+cocotb19:py:attr:`BinaryValue.buff <cocotb.binary.BinaryValue.buff>`,
:external+cocotb19:py:attr:`BinaryValue.binstr <cocotb.binary.BinaryValue.binstr>`,
:external+cocotb19:py:attr:`BinaryValue.integer <cocotb.binary.BinaryValue.signed_integer>`,
or :external+cocotb19:py:attr:`BinaryValue.signed_integer <cocotb.binary.BinaryValue.signed_integer>` setters,
if the provided value was smaller than the :class:`!BinaryValue`,
the value would be zero-extended based on the endianness of :class:`!BinaryValue`.

:class:`!LogicArray` has no concept of "bit-endianness" as the indexing scheme is arbitrary.
When partially setting a :class:`!LogicArray`, you are expected to explicitly provide the slice you want to set,
and it must match the size of the value it's being set with.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    b = BinaryValue(0, 4, bigEndian=True)
    b.binstr = "1"
    assert b == "1000"
    b.integer = 2
    assert b == "1000"  # Surprise!

    c = BinaryValue(0, 4, bigEndian=False)
    c.binstr = "1"
    assert c == "0001"
    c.integer = 2
    assert c == "0010"

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    val = LogicArray(0, Range(0, 3))
    val[0] = "1"
    assert val == "1000"
    val[0:1] = 0b01
    assert val == "0100"

.. note::
    :class:`!LogicArray` supports setting its value with the deprecated :attr:`.LogicArray.buff`,
    :attr:`.LogicArray.binstr`, :attr:`.LogicArray.integer` and :attr:`.LogicArray.signed_integer` setters,
    but assumes the value matches the width of the whole :class:`!LogicArray`.
    Values that are too big or too small will result in a :exc:`ValueError`.


Implicit truncation
-------------------

Conversely, when modifying a :class:`!BinaryValue` in-place,
if the provided value is too large, it would be implicitly truncated and issue a :exc:`RuntimeWarning`.
In certain circumstances, the :exc:`!RuntimeWarning` wouldn't be issued.

:class:`LogicArray`, as stated in the previous section,
requires the user to provide a value the same size as the slice to be set.
Failure to do so will result in a :exc:`ValueError`.

.. code-block:: python
    :caption: Old way with :class:`!BinaryValue`
    :class: removed

    b = BinaryValue(0, 4, bigEndian=True)
    b.binstr = "00001111"
    # RuntimeWarning: 4-bit value requested, truncating value '00001111' (8 bits) to '1111'
    assert b == "1111"
    b.integer = 100
    # RuntimeWarning: 4-bit value requested, truncating value '1100100' (7 bits) to '0100'
    assert b == "0100"

    c = BinaryValue(0, 4, bigEndian=False)
    c.binstr = "00001111"
    # No RuntimeWarning?
    assert c == "1111"  # Surprise!
    c.integer = 100
    # RuntimeWarning: 4-bit value requested, truncating value '1100100' (7 bits) to '110'
    assert c == "110"  # ???

.. code-block:: python
    :caption: New way with :class:`!LogicArray`
    :class: new

    val = LogicArray(0, 4)
    # val[:] = "00001111"  # ValueError: Value of length 8 will not fit in Range(3, 'downto', 0)
    # val[:] = 100         # ValueError: 100 will not fit in a LogicArray with bounds: Range(3, 'downto', 0)
    val[3:0] = "00001111"[:4]
    assert val == "0000"
    val[3:0] = LogicArray.from_unsigned(100, 8)[3:0]
    assert val == "0100"

.. note::
    :class:`!LogicArray` supports setting its value with the deprecated :attr:`.LogicArray.buff`,
    :attr:`.LogicArray.binstr`, :attr:`.LogicArray.integer` and :attr:`.LogicArray.signed_integer` setters,
    but assumes the value matches the width of the whole :class:`!LogicArray`.
    Values that are too big or too small will result in a :exc:`ValueError`.


Integer representation
----------------------

:class:`!BinaryValue` could be constructed with a ``binaryRepresentation`` argument of the type :external+cocotb19:py:class:`~cocotb.binary.BinaryRepresentation`
which would select how that :class:`!BinaryValue` would interpret any integer being used to set its value.
:external+cocotb19:py:meth:`BinaryValue.assign <cocotb.binary.BinaryValue.assign>`
and the :external+cocotb19:py:attr:`BinaryValue.integer <cocotb.binary.BinaryValue.signed_integer>`
and :external+cocotb19:py:attr:`BinaryValue.signed_integer <cocotb.binary.BinaryValue.signed_integer>` setters all behaved the same when given an integer.
Unlike endianness, this could not be changed after construction (setting :attr:`!BinaryValue.binaryRepresentation` has no effect).

:class:`!LogicArray` does not have a concept of integer representation as a part of its value,
its value is just an array of :class:`!Logic`.
Integer representation is provided when converting to and from an integer.

.. note::
    :class:`!LogicArray` interfaces that can take integers are expected to take them as "bit array literals", e.g. ``0b110101`` or ``0xFACE``.
    That is, they are interpreted as if they are unsigned integer values.

.. note::
    :class:`!LogicArray` supports setting its value with the deprecated :attr:`.LogicArray.integer` and :attr:`.LogicArray.signed_integer` setters,
    but assumes an unsigned and two's complement representation, respectively.


.. _logic-handle-value-changes:

**************************************************************************************************************************************
Expect :class:`!LogicArray` and :class:`!Logic` instead of :class:`!BinaryValue` when getting values from logic-like simulator objects
**************************************************************************************************************************************

Change
======

Handles to logic-like simulator objects now return :class:`.LogicArray` or :class:`.Logic` instead of :external+cocotb19:py:class:`~cocotb.binary.BinaryValue`
when getting their value with the :attr:`value <cocotb.handle.ValueObjectBase.value>` getter.
Scalar logic-like simulator objects return :class:`!Logic`, and array-of-logic-like simulator objects return :class:`!LogicArray`.

How to Upgrade
==============

:ref:`logic-array-over-binary-value` when dealing with array-of-logic-like simulator objects.
Change code when dealing with scalar logic-like simulator objects to work with :class:`!Logic`.

Change indexing assumptions from always being ``0`` to ``length-1`` left-to-right, to following the arbitrary indexing scheme of the logic array as defined in HDL.
See :ref:`update-indexing` for more details on how to update indexing and slicing.

Rationale
=========

See the rationale for switching from :class:`!BinaryValue` to :class:`!LogicArray`.
The change to use the HDL indexing scheme makes usage more intuitive for new users and eases debugging.
Scalars and arrays of logic handles were split into two types with different value types so that handles to arrays could support
getting :func:`length <len>` and indexing information: :meth:`.LogicArrayObject.left`, :meth:`.LogicArrayObject.right`, :meth:`.LogicArrayObject.direction`, and :meth:`.LogicArrayObject.range`,
which cause errors when applied to scalar objects.

Additional Details
==================

Operations such as equality with and conversion to :class:`int`, :class:`str`, and :class:`bool`,
as well as getting the :func:`length <len>`,
work the same for :class:`!Logic`, :class:`!LogicArray`, and :class:`!BinaryValue`.
This was done deliberately to reduce the number of changes required,
while also providing a common API to enable writing backwards-compatible and higher-order APIs.

.. code-block:: python
    :caption: Works with :class:`!BinaryValue` in cocotb 1.x and both :class:`!Logic` and :class:`!LogicArray` in cocotb 2.x.

    assert len(dut.signal.value) == 1
    assert dut.signal.value == 1
    assert dut.signal.value == "1"
    assert dut.signal.value == True
    assert int(dut.signal.value) == 1
    assert str(dut.signal.value) == "1"
    assert bool(dut.signal.value) is True
    dut.signal.value = 1
    dut.signal.value = "1"
    dut.signal.value = True


.. _array-handle-value-changes:

***************************************************************************************************
Expect :class:`!Array` instead of :class:`!list` when getting values from arrayed simulator objects
***************************************************************************************************

Change
======

Handles to arrayed simulator objects now return :class:`.Array` instead of :class:`list` when getting values with the :attr:`value <cocotb.handle.ValueObjectBase.value>` getter.

How to Upgrade
==============

Change indexing assumptions from always being ``0`` to ``length-1`` left-to-right, to following the arbitrary indexing scheme of the array as defined in HDL.
See :ref:`update-indexing` for more details on how to update indexing and slicing.

Rationale
=========

:class:`!Array` provides most features of :class:`!list` besides the fact that it is immutable in size and uses arbitrary indexing, like :class:`.LogicArray`.
The change to use the HDL indexing scheme makes usage more intuitive for new users and eases debugging.

Additional Details
==================

Equality with and conversion to :class:`!list`,
getting the :func:`length <len>`,
and iteration,
works the same for both the old way and the new way using :class:`!Array`.
This was done deliberately to reduce the number of changes required.

.. code-block:: python
    :caption: Works with both :class:`!list` in cocotb 1.x and :class:`!Array` in cocotb 2.x.

    assert dut.array.value == [1, 2, 3, 4]
    as_list = list(dut.array.value)
    assert as_list[0] == 1
    assert len(dut.array.value) == 4
    for actual, expected in zip(dut.array.value, [1, 2, 3, 4]):
        assert actual == expected


****************************************************************
Use :deco:`!cocotb.parametrize` instead of :class:`!TestFactory`
****************************************************************

Change
======

:class:`cocotb.parametrize` was added to replace :class:`.TestFactory`, which was deprecated.

How to Upgrade
==============

Replace all instances of :class:`!TestFactory` with a :deco:`!cocotb.parametrize` decorator on the function being parameterized.

Replace calls to :meth:`.TestFactory.add_option` with arguments to :deco:`!cocotb.parametrize`.

Remove all calls to :meth:`.TestFactory.generate_tests` and move any arguments to the :deco:`cocotb.test` decorator.

.. code-block:: python
    :caption: Old way with :class:`!TestFactory`
    :class: removed

    async def my_test(param_a, param_b):
        ...

    tf = TestFactory(my_test)
    tf.add_option("param_a", [1, 2, 3])
    tf.add_option("param_b", ["sample", "text"])
    tf.generate_tests(timeout_time=10, timeout_unit="us")

.. code-block:: python
    :caption: New way with :deco:`!cocotb.parametrize`
    :class: new

    @cocotb.test(timeout_time=10, timeout_unit="us")
    @cocotb.parametrize(
        param_a=[1, 2, 3],
        param_b=["sample", "text"]
    )
    async def my_test(param_a, param_b):
        ...

.. note::

    If you are using the ``prefix`` or ``postfix`` arguments to :meth:`!TestFactory.generate_tests`,
    replace them with the use of the new ``name`` argument.

Rationale
=========

:class:`!TestFactory` was defined separately from the test declaration, hurting readability,
and making it prone to issues such as parameters being out of sync
and :deco:`cocotb.test` inadvertently being applied to the parameterized function.
Additionally it worked by injecting test objects into the module of the calling scope,
which led to feature creep (``stacklevel`` arg to :meth:`!TestFactory.generate_tests`)
and made issues hard to diagnose.
Next, the test names generated were *not* descriptive and did not lend themselves to being filtered with a regular expression.
Finally, it doesn't compose well with future test marking features.

:deco:`!cocotb.parametrize` has none of those issues and should be familiar to users of :mod:`pytest`.
Generated test names are descriptive and can be easily filtered with a regular expression.

**********************************************************
Move away from :data:`!Event.data` and :data:`!Event.name`
**********************************************************

Change
======

The :data:`.Event.data` attribute and ``data`` argument to the :meth:`.Event.set` method,
and the :data:`.Event.name` attribute and ``name`` argument to the :class:`.Event` constructor were deprecated.

How to Upgrade
==============

Remove all passing of the ``name`` argument to the :class:`!Event` constructor.

Remove all passing of the ``data`` argument to the :meth:`!Event.set` method and uses of the :data:`!Event.data` attribute.
Replace with an adjacent variable or class attribute.

.. code-block:: python
    :caption: Old way using :data:`!Event.data`
    :class: removed

    monitor_event = Event()

    ...  # in monitor
    monitor_event.set(b"\xBA\xD0\xCA\xFE")

    ...  # in user code
    await monitor_event.wait()
    recv = monitor_event.data

.. code-block:: python
    :caption: New way using an adjacent variable
    :class: new

    monitor_event = Event()
    monitor_data = None

    ...  # in monitor
    monitor_data = b"\xBA\xD0\xCA\xFE"
    monitor_event.set()

    ...  # in user code
    await monitor_event.wait()
    recv = monitor_data

Rationale
=========

These features were removed to better align cocotb's :class:`!Event` with :class:`asyncio.Event`.


****************************************************
Remove uses of :class:`!Join` and :meth:`!Task.join`
****************************************************

Change
======

:class:`.Join` and :meth:`.Task.join` have been deprecated.

How to Upgrade
==============

Remove :class:`!Join` and :meth:`!Task.join` and simply :keyword:`await` the :class:`!Task` being joined,
or pass the :class:`!Task` directly into the function that will :keyword:`await` it.

.. code-block:: python
    :caption: Example Task

    async def example():
        ...

    task = cocotb.start_soon()

.. code-block:: python
    :caption: Old way using :class:`!Join`
    :class: removed

    await Join(task)
    # or
    await First(Join(task), RisingEdge(cocotb.top.clk))

.. code-block:: python
    :caption: Old way using :meth:`!Task.join`
    :class: removed

    await task.join()
    # or
    await First(task.join(), RisingEdge(cocotb.top.clk))

.. code-block:: python
    :caption: New way using :class:`!Task` directly
    :class: new

    await task
    # or
    await First(task, RisingEdge(cocotb.top.clk))

Rationale
=========

There were multiple synonyms for the same functionality, so we deprecated all but the least verbose.
This also better aligns cocotb's :class:`!Task`\ s with :class:`asyncio.Task`.

Additional Details
==================

:keyword:`await`\ ing a :class:`!Task` (or previously a :class:`!Join` trigger) returns the result of the :class:`!Task`, not the task/trigger.
This can make it difficult to determine which :class:`!Task` finished when waiting on multiple, such as with a :class:`.First` trigger.
:class:`.TaskComplete` was added to solve this.
Use :attr:`.Task.complete` to get the :class:`!TaskComplete` trigger associated with each :class:`!Task`.

.. code-block:: python
    :caption: Using :class:`!TaskComplete` to disambiguate which :class:`!Task` finished.
    :class: new

    async def coro1():
        await Timer(1, 'us')

    async def coro2():
        await RisingEdge(cocotb.top.done)

    task1 = cocotb.start_soon(coro1())
    task2 = cocotb.start_soon(coro2())

    # res = await First(task1, task2)
    # res is `None` is either case, which fired?

    res = await First(task1.complete, task2.complete)

    if res is task1.complete:
        cocotb.log.info("Reached deadline!")
    else:
        cocotb.log.info("Processing finished!")


****************************************************
Replace :meth:`!Task.kill` with :meth:`!Task.cancel`
****************************************************

Change
======

:meth:`.Task.kill` was replaced with :meth:`.Task.cancel`.

How to Upgrade
==============

Replace calls of :meth:`!Task.kill` with :meth:`!Task.cancel`.

.. code-block:: python
    :caption: Old way using :meth:`!Task.kill`
    :class: removed

    task.kill()

.. code-block:: python
    :caption: New way using :meth:`!Task.cancel`
    :class: new

    task.cancel()

Rationale
=========

:meth:`!Task.kill` stopped a :class:`.Task` from executing immediately,
which required re-entering the scheduler from a user context.
Scheduler re-entrance has been the cause of several hard to diagnose bugs.
:meth:`!Task.cancel` *schedules* stopping a :class:`!Task`,
preventing scheduler re-entrancy and sidestepping an entire class of bugs.

Additionally, :meth:`!Task.cancel` throws a :exc:`!CancelledError` into the task during cancellation,
allowing cleanup code to be executed, which was not the case with :meth:`Task.kill`.

Additional Details
==================

:class:`!Task`\ s don't become "done" immediately
-------------------------------------------------

There is a slight change in behavior when moving to :meth:`!Task.cancel` since it *schedules* a cancellation.
:class:`!Task`\ s don't become "done" immediately, but only after control is returned to the scheduler.

.. code-block:: python
    :caption: Old way using :meth:`!Task.kill`
    :class: removed

    task.kill()
    assert task.done()

.. code-block:: python
    :caption: New way using :meth:`!Task.cancel`
    :class: new

    task.cancel()
    assert not task.done()
    await NullTrigger()
    assert task.done()

This can cause a change in scheduling when :keyword:`await`\ ing a :class:`!Task` to finish if it is cancelled instead of killed.

:exc:`!CancelledError` is thrown into cancelled :class:`Task`\ s
----------------------------------------------------------------

When a :class:`!Task` is cancelled by calling :meth:`!Task.cancel`,
a :exc:`asyncio.CancelledError` is thrown into the task.
This ensures cleanup is performed.
:term:`context manager`\ s doing cleanup on exit and any :keyword:`finally` blocks in your tasks
will now be executed when the task is cancelled.
Otherwise, the exception will bubble up through your code and be handled appropriately by :class:`!Task` internals,
so there is nothing else you have to do.

All :class:`!Task`\ s created with :func:`cocotb.start_soon`, :func:`cocotb.start`, or :func:`cocotb.create_task`
that are still running at the end of the test will be cancelled to ensure end-of-test cleanup.

.. code-block:: python
    :caption: Example of how :exc:`!CancelledError` ensures cleanup

    async def stimulus():
        try:
            with open("transactions.log", "w") as f:
                transaction = 123
                f.write(transaction)
            # The context manager exited here, so the file was closed. This happens
            # whether it exited normally, threw an exception, the task was cancelled,
            # or the test ended.
        finally:
            # The finally block is always executed. This happens whether the try block
            # exited normally, an exception was thrown, the task was cancelled, or the test ended.
            cocotb.log.info("Ending stimulus!")

:exc:`!CancelledError` thrown during cancellation cannot be squashed
--------------------------------------------------------------------

Unlike :mod:`asyncio`, task cancellation *cannot* be ignored.
When a test ends all tasks *must* be cancelled,
otherwise they would continue running into the next test.
To ensure that users don't inadvertently ignore cancellation,
cocotb forces the task to end with :exc:`RuntimeError` if it detects a :exc:`!CancelledError` is squashed.

When upgrading code to 2.0, there may be existing code which causes this condition to fire.
The most common offender is user code catching :exc:`BaseException`.

.. code-block:: python
    :caption: Code which will accidentally squash :exc:`!CancelledError`
    :class: removed

    async def example():
        try:
            ...
        except BaseException as e:
            cocotb.log.info("Saw error!", exc_info=e)

:exc:`!BaseException` is generally reserved for runtime implementation details.
Instead catch only :exc:`Exception`.

.. code-block:: python
    :caption: Resolving issue by catching only :exc:`!Exception`
    :class: new

    async def example():
        try:
            ...
        except Exception as e:
            cocotb.log.info("Saw error!", exc_info=e)

If narrowing your exception handling to :exc:`Exception` isn't possible,
explicitly catch :exc:`!CancelledError` and re-raise it in an except clause placed *before* the :exc:`!BaseException` clause.

.. code-block:: python
    :caption: Resolving issue by explicitly catching :exc:`!CancelledError`
    :class: new

    async def example():
        try:
            ...
        except asyncio.CancelledError:
            raise
        except BaseException as e:
            cocotb.log.info("Saw error!", exc_info=e)


*************************************************************
Replace :func:`!cocotb.start` with :func:`!cocotb.start_soon`
*************************************************************

Change
======

:func:`cocotb.start` was deprecated.

How to Upgrade
==============

Replace :func:`!cocotb.start` with :func:`cocotb.start_soon` and remove the :keyword:`await` before it.

.. code-block:: python
    :caption: Old way using :func:`!cocotb.start`
    :class: removed

    async def my_coro():
        ...  # do stuff

    my_task = await cocotb.start(my_coro())

.. code-block:: python
    :caption: New way using :func:`!cocotb.start_soon`
    :class: new

    async def my_coro():
        ...  # do stuff

    my_task = cocotb.start_soon(my_coro())

.. note::

    If you need the started Task to run *immediately* rather than *soon*,
    :keyword:`!await` a :class:`.NullTrigger` immediately after calling :func:`!cocotb.start_soon`.
    This is not common.

    .. code-block:: python
        :caption: Using :class:`!NullTrigger` to force a new Task to run

            async def my_coro():
                ...  # do stuff

            my_task = cocotb.start_soon(my_coro())
            # my_task isn't running
            await NullTrigger()
            # my_task is now running

Rationale
=========

Many new users were confused on when to use one vs the other,
so :func:`!cocotb.start` will be removed to prevent any confusion.


*********************************************************************************
Replace ``handle.setimmediatevalue(value)`` with ``handle.set(Immediate(value))``
*********************************************************************************

Change
======

:meth:`handle.setimmediatevalue() <cocotb.handle.ValueObjectBase.setimmediatevalue>` was deprecated.

How To Upgrade
==============

Replace the call to :meth:`!handle.setimmediatevalue` with a value set using the :meth:`~cocotb.handle.Immediate` action wrapper.

.. code-block:: python
    :caption: Old way with ``handle.setimmediatevalue(value)``
    :class: removed

    cocotb.top.iface.valid.setimmediatevalue(0)

.. code-block:: python
    :caption: New way with ``handle.set(Immediate(value))``
    :class: new

    cocotb.top.iface.valid.set(Immediate(0))

Rationale
=========

:meth:`!handle.setimmediatevalue` does not actually set the object's value immediately.
It sets the value inertially, but immediately,
without it being scheduled for the next :ref:`ReadWrite sync phase <values-settle>`.
This means signals get their value at delta N+1 (N being where you currently are in the time step).
This is unexpected and generally not useful.

:class:`!Immediate` applies values immediately, such that they can be read back after writing.

.. code-block:: python
    :caption: Read back value written immediately
    :class: new

    assert cocotb.top.data.value == 100
    cocotb.top.data.set(Immediate(0))
    # new value can be read back immediately
    assert cocotb.top.data.value == 0


********************************************************************
Use :func:`!cocotb.pass_test` instead of raising :exc:`!TestSuccess`
********************************************************************

Change
======

:external+cocotb19:py:exc:`~cocotb.result.TestSuccess` was deprecated and replaced with :func:`cocotb.pass_test`.

How To Upgrade
==============

Replace ``raise TestSuccess(msg)`` with a call to :func:`!cocotb.pass_test`.

.. code-block:: python
    :caption: Old way with :exc:`!TestSuccess`
    :class: removed

    if cocotb.top.error.value == 0:
        raise TestSuccess("Test finished without DUT erroring")

.. code-block:: python
    :caption: New way with :func:`!cocotb.pass_test`
    :class: new

    if cocotb.top.error.value == 0:
        cocotb.pass_test("Test finished without DUT erroring")

Rationale
=========

cocotb needs a way to end a test with a pass from any Task, not just the main test Task.
:exc:`!TestSuccess` was created for that purpose.
But being an exception, it has an additional implied interface:

- It is acceptable to catch it.
- It will propagate through Tasks like other exceptions do.

However, neither of these implied behaviors is actually supported.

:func:`!cocotb.pass_test` being a function call avoids these implicit interfaces.
It also parallels the design of :func:`sys.exit`.


*******************************************************************
Fail tests using :keyword:`!assert` rather than :exc:`!TestFailure`
*******************************************************************

Change
======

:external+cocotb19:py:exc:`~cocotb.result.TestFailure` was removed.

How to Upgrade
==============

Replace ``raise TestFailure(msg)`` with an :keyword:`assert` statement.
Move any exception message to the optional message clause of the :keyword:`!assert` statement.

.. code-block:: python
    :caption: Old way with :exc:`!TestFailure`
    :class: removed

    if cocotb.top.error.value != 0:
        raise TestFailure("DUT errored")

.. code-block:: python
    :caption: New way with :keyword:`!assert`
    :class: new

    assert cocotb.top.error.value == 0, "DUT errored"

Rationale
=========

cocotb had far too many competing ways to fail a test, so they were reduced to one.
:keyword:`assert` is already familiar to those who have ever used :mod:`pytest`,
and :mod:`!pytest` functionality can be leveraged to rewrite the :exc:`AssertionError`\ s coming from failing :keyword:`!assert`\ s
with more contextual information as to why the :keyword:`!assert` failed.


*********************************
Replace uses of :exc:`!TestError`
*********************************

Change
======

:external+cocotb19:py:exc:`~cocotb.result.TestError` was removed.

How to Upgrade
==============

Replace :exc:`!TestError` with an :external+python:ref:`exception of the appropriate type <concrete-exceptions>`.

.. code-block:: python
    :caption: Old way with :exc:`!TestError`
    :class: removed

    def drive(pkt):
        if not isinstance(pkt, bytes):
            raise TestError("packet must be bytes")
        ...

.. code-block:: python
    :caption: New way with more appropriate exception type
    :class: new

    def drive(pkt):
        if not isinstance(pkt, bytes):
            raise TypeError("packet must be bytes")
        ...

Rationale
=========

:exc:`TestError` is unnecessarily cocotb-specific and another redundant way to fail the test with an error,
so it was removed.


****************************************************************************************************
Use ``sources`` argument in :meth:`Runner.build` instead of ``vhdl_sources`` and ``verilog_sources``
****************************************************************************************************

Change
======

The ``vhdl_sources`` and ``verilog_sources`` arguments to :meth:`.Runner.build` have been deprecated and replaced with the ``sources`` argument.

How to Upgrade
==============

Instead of splitting your sources between the ``vhdl_sources`` and ``verilog_sources`` arguments,
pass all sources via the ``sources`` argument.
Sources will be compiled in the given order, left-to-right.

.. code-block:: python
    :caption: Old way with ``vhdl_sources`` and ``verilog_sources``
    :class: removed

    runner = get_runner()
    runner.build(
        vhdl_sources=["top.vhdl"],
        verilog_sources=["ip_core.sv"],
    )

.. code-block:: python
    :caption: New way with ``sources``
    :class: new

    runner = get_runner()
    runner.build(
        sources=["ip_core.sv", "top.vhdl"],
    )

.. note::
    If you are unsure about the order the sources should be compiled in with mixed-language simulators,
    prefer compiling all VHDL sources, then all Verilog sources.
    This is the order of compilation when using separate ``vhdl_sources`` and ``verilog_sources`` arguments.

Rationale
=========

Splitting the two types of sources made arbitrary build ordering of VHDL and Verilog sources impossible.
This approach also reduces verbosity and hidden assumptions about compilation order.

Additional Details
==================

Source files are judged to be either VHDL or Verilog sources and compiled appropriately for your simulator.
The runner uses the file extension to determine whether the source file is VHDL or Verilog
(see :meth:`.Runner.build` for details).
If you use custom file extensions,
you can use the :class:`~cocotb_tools.runner.VHDL` and :class:`~cocotb_tools.runner.Verilog` tag classes
to mark the sources as either VHDL or Verilog, respectively.

.. code-block:: python

    runner = get_runner()
    runner.build(
        sources=[Verilog("ip_core.gen"), "top.vhdl"],
    )


********************************************************************
Use :data:`!cocotb.log` over loggers on handles, tasks, and triggers
********************************************************************

Change
======

``handle._log``,
``Task.log``,
and ``Trigger.log`` were made private.
All loggers in the ``"cocotb"`` namespace were reserved for internal use only.
:data:`cocotb.log` was changed to be the ``"test"`` logger.

How To Upgrade
==============

Replace all uses of the loggers on cocotb objects with :data:`!cocotb.log`.
Use the :func:`repr` of the object in the message if desired.

.. code-block:: python
    :caption: Old way with ``"cocotb"`` namespace loggers.
    :class: removed

    cocotb.top.signal._log.info("logging from a handle")

    task = cocotb.start_soon(example())
    task.log.info("logging from a task")

    trigger = Timer(10, 'ns')
    trigger.log.info("logging from a trigger")

.. code-block:: python
    :caption: New way with :data:`!cocotb.log`
    :class: new

    cocotb.log.info("%r: logging from a handle", cocotb.top.signal)

    task = cocotb.start_soon(example())
    cocotb.log.info("%r: logging from a task", task)

    trigger = Timer(10, 'ns')
    cocotb.log.info("%r: logging from a trigger", trigger)

Rationale
=========

The ``"cocotb"`` logging namespace was reserved for cocotb internal use
so that it can offer users better control over the verbosity of those messages.
As a result, the :data:`!cocotb.log` logger name was changed from ``"cocotb"``
and all loggers on cocotb internal objects were made private (these loggers were in the ``"cocotb"`` namespace).


****************************************************************
Use :meth:`!handle.is_const` instead of :class:`!ConstantObject`
****************************************************************

Change
======

:external+cocotb19:py:class:`~cocotb.handle.ConstantObject` was removed.
:attr:`handle.is_const <cocotb.handle.ValueObjectBase.is_const>` was added to replace it.

How to Upgrade
==============

Replace uses of ``isinstance(handle, ConstantObject)`` as a way to check the constant-ness of a simulator object
with checking the handle's :attr:`is_const` attribute.

.. code-block:: python
    :caption: Old way with :class:`!ConstantObject`
    :class: removed

    if isinstance(cocotb.top.PARAM, ConstantObject):
        ...

.. code-block:: python
    :caption: New way with :attr:`is_const`
    :class: new

    if cocotb.top.PARAM.is_const:
        ...


Rationale
=========

:class:`!ConstantObject` was a single type that serviced all constant objects regardless of their data type.
This made it fragile to users getting the data type incorrect and values being applied incorrectly or causing crashes.
Now constant objects are mapped to the appropriate handle type and these issues can't occur.
