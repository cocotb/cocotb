Tutorial: Driver Cosimulation
=============================

Cocotb was designed to provide a common platform for hardware and software
developers to interact.  By integrating systems early, ideally at the
block level, it's possible to find bugs earlier in the design process.

For any given component that has a software interface there is typically a
software abstraction layer or driver which communicates with the hardware. In
this tutorial we will call unmodified production software from our testbench
and re-use the code written to configure the entity.

For the impatient this tutorial is provided as an example with Cocotb. You can
run this example from a fresh checkout::

    cd examples/endian_swapper/tests
    make MODULE=test_endian_swapper_hal

.. note:: `SWIG`_ is required to compile the example




Difficulties with Driver Co-simulation
--------------------------------------

Co-simulating *un-modified* production software against a block-level
testbench is not trivial - there are a couple of significant obstacles to
overcome:


Calling the HAL from a test
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Typically the software component (often referred to as a Hardware Abstraction
Layer or HAL) is written in C.  We need to call this software from our test
written in Python.  There are multiple ways to call C code from Python, in
this tutorial we'll use `SWIG`_ to generate Python bindings for our HAL.


Blocking in the driver
~~~~~~~~~~~~~~~~~~~~~~

Another difficulty to overcome is the fact that the HAL is expecting to call
a low-level function to access the hardware, often something like ``ioread32``.
We need this call to block while simulation time advances and a value is
either read or written on the bus.  To achieve this we link the HAL against
a C library that provides the low level read/write functions.  These functions
in turn call into Cocotb and perform the relevant access on the DUT.


Cocotb infrastructure
---------------------

There are two decorators provided to enable this flow, which are typically used
together to achieve the required functionality.  The ``cocotb.external``
decorator turns a normal function that isn't a coroutine into a blocking
coroutine (by running the function in a separate thread).  The 
``cocotb.function`` decorator allows a coroutine that consumes simulation time
to be called by a normal thread.  The call sequence looks like this:


.. image:: diagrams/svg/hal_cosimulation.*


Implementation
--------------


Register Map
~~~~~~~~~~~~

The endian swapper has a very simple register map:

+-------------+-------------+------+--------+------------+
| Byte Offset | Register    | Bits | Access | Description|
+=============+=============+======+========+============+
|0            | CONTROL     |  0   | R/W    | Enable     |
|             |             +------+--------+------------+
|             |             | 31:1 | N/A    | Reserved   |
+-------------+-------------+------+--------+------------+
|4            |PACKET_COUNT | 31:0 | RO     | Num Packets|
+-------------+-------------+------+--------+------------+


HAL
~~~

To keep things simple we use the same RTL from the :doc:`endian_swapper`. We
write a simplistic HAL which provides the following functions:


.. code-block:: c

    endian_swapper_enable(endian_swapper_state_t *state);
    endian_swapper_disable(endian_swapper_state_t *state);
    endian_swapper_get_count(endian_swapper_state_t *state);


These functions call ``IORD`` and ``IOWR`` - usually provided by the Altera
NIOS framework.


IO Module
~~~~~~~~~

This module acts as the bridge between the C HAL and the Python testbench.  It
exposes the ``IORD`` and ``IOWR`` calls to link the HAL against, but also
provides a Python interface to allow the read/write bindings to be dynamically
set (through ``set_write_function`` and ``set_read_function`` module functions).

In a more complicated scenario, this could act as an interconnect, dispatching
the access to the appropriate driver depending on address decoding, for
instance.


Testbench
~~~~~~~~~

First of all we set up a clock, create an Avalon Master interface and reset
the DUT.  Then we create two functions that are wrapped with the 
``cocotb.function`` decorator to be called when the HAL attempts to perform
a read or write.  These are then passed to the `IO Module`_:


.. code-block:: python


    @cocotb.function
    def read(address):
        master.log.debug("External source: reading address 0x%08X" % address)
        value = yield master.read(address)
        master.log.debug("Reading complete: got value 0x%08x" % value)
        raise ReturnValue(value)

    @cocotb.function
    def write(address, value):
        master.log.debug("Write called for 0x%08X -> %d" % (address, value))
        yield master.write(address, value)
        master.log.debug("Write complete")

    io_module.set_write_function(write)
    io_module.set_read_function(read)


We can then intialise the HAL and call functions, using the ``cocotb.external``
decorator to turn the normal function into a blocking coroutine that we can
``yield``:


.. code-block:: python

    state = hal.endian_swapper_init(0)
    yield cocotb.external(hal.endian_swapper_enable)(state)


The HAL will perform whatever calls it needs, accessing the DUT through the
Avalon-MM driver, and control will return to the testbench when the function
returns.

.. note:: The decorator is applied to the function before it is called



Further Work
------------

In future tutorials we'll consider co-simulating unmodified drivers written 
using ``mmap`` (for example built upon the `UIO framework`_) and consider 
interfacing with emulators like `QEMU`_ to allow us to co-simulate when the
software needs to execute on a different processor architecture.


.. _SWIG: http://www.swig.org/

.. _UIO framework: https://www.kernel.org/doc/htmldocs/uio-howto/about.html

.. _QEMU: http://wiki.qemu.org/Main_Page


