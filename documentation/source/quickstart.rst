################
Quickstart Guide
################

Installing cocotb
=================

Pre-requisites
--------------

Cocotb has the following requirements:

* Python 2.7, Python 3.5+ (recommended)
* Python-dev packages
* GCC and associated development packages
* GNU Make
* A Verilog or VHDL simulator, depending on your RTL source code

Installation via PIP
--------------------

.. versionadded:: 1.2

Cocotb can be installed by running

.. code-block:: bash

    $> pip3 install cocotb

or

.. code-block:: bash

    $> pip install cocotb

For user local installation follow the
`pip User Guide <https://https://pip.pypa.io/en/stable/user_guide/#user-installs/>`_.

To install the development version of cocotb:

.. code-block:: bash

    $> git clone https://github.com/cocotb/cocotb
    $> pip install -e ./cocotb


Native Linux Installation
-------------------------

The following instructions will allow building of the cocotb libraries
for use with a 64-bit native simulator.

If a 32-bit simulator is being used then additional steps are needed, please see
`our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.

Debian/Ubuntu-based

.. code-block:: bash

    $> sudo apt-get install git make gcc g++ swig python-dev

RedHat-based

.. code-block:: bash

    $> sudo yum install gcc gcc-c++ libstdc++-devel swig python-devel


Windows Installation
--------------------

Download the MinGW installer from https://osdn.net/projects/mingw/releases/.

Run the GUI installer and specify a directory you would like the environment
installed in. The installer will retrieve a list of possible packages, when this
is done press "Continue". The MinGW Installation Manager is then launched.

The following packages need selecting by checking the tick box and selecting
"Mark for installation"

.. code-block:: bash

    Basic Installation
      -- mingw-developer-tools
      -- mingw32-base
      -- mingw32-gcc-g++
      -- msys-base

From the Installation menu then select "Apply Changes", in the next dialog
select "Apply".

When installed a shell can be opened using the "msys.bat" file located under
the <install_dir>/msys/1.0/

Python can be downloaded from https://www.python.org/downloads/windows/.
Run the installer and download to your chosen location.

It is beneficial to add the path to Python to the Windows system ``PATH`` variable
so it can be used easily from inside Msys.

Once inside the Msys shell commands as given here will work as expected.

macOS Packages
--------------

You need a few packages installed to get cocotb running on macOS.
Installing a package manager really helps things out here.

`Brew <https://brew.sh/>`_ seems to be the most popular, so we'll assume you have that installed.

.. code-block:: bash

    $> brew install python icarus-verilog gtkwave


Running your first Example
==========================

Assuming you have installed the prerequisites as above,
the following lines are all you need to run a first simulation with cocotb:

.. code-block:: bash

    $> git clone https://github.com/cocotb/cocotb
    $> cd cocotb/examples/endian_swapper/tests
    $> make

Selecting a different simulator is as easy as:

.. code-block:: bash

    $> make SIM=vcs


Running the same example as VHDL
--------------------------------

The ``endian_swapper`` example includes both a VHDL and a Verilog RTL implementation.
The cocotb testbench can execute against either implementation using VPI for
Verilog and VHPI/FLI for VHDL.  To run the test suite against the VHDL
implementation use the following command (a VHPI or FLI capable simulator must
be used):

.. code-block:: bash

    $> make SIM=ghdl TOPLEVEL_LANG=vhdl


Using cocotb
============

A typical cocotb testbench requires no additional HDL code (though nothing prevents you from adding testbench helper code).
The Design Under Test (DUT) is instantiated as the toplevel in the simulator
without any wrapper code.
Cocotb drives stimulus onto the inputs to the DUT and monitors the outputs
directly from Python.


Creating a Makefile
-------------------

To create a cocotb test we typically have to create a Makefile.  Cocotb provides
rules which make it easy to get started.  We simply inform cocotb of the
source files we need compiling, the toplevel entity to instantiate and the
Python test script to load.

.. code-block:: makefile

    VERILOG_SOURCES = $(PWD)/submodule.sv $(PWD)/my_design.sv
    # TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file:
    TOPLEVEL=my_design
    # MODULE is the name of the Python test file:
    MODULE=test_my_design

    include $(shell cocotb-config --makefiles)/Makefile.inc
    include $(shell cocotb-config --makefiles)/Makefile.sim

We would then create a file called ``test_my_design.py`` containing our tests.


Creating a test
---------------

The test is written in Python. Cocotb wraps your top level with the handle you
pass it. In this documentation, and most of the examples in the project, that
handle is ``dut``, but you can pass your own preferred name in instead. The
handle is used in all Python files referencing your RTL project. Assuming we
have a toplevel port called ``clk`` we could create a test file containing the
following:

.. code-block:: python3

    import cocotb
    from cocotb.triggers import Timer

    @cocotb.test()
    def my_first_test(dut):
        """Try accessing the design."""

        dut._log.info("Running test!")
        for cycle in range(10):
            dut.clk = 0
            yield Timer(1000)
            dut.clk = 1
            yield Timer(1000)
        dut._log.info("Running test!")

This will drive a square wave clock onto the ``clk`` port of the toplevel.


Accessing the design
--------------------

When cocotb initialises it finds the top-level instantiation in the simulator
and creates a handle called ``dut``. Top-level signals can be accessed using the
"dot" notation used for accessing object attributes in Python. The same mechanism
can be used to access signals inside the design.

.. code-block:: python3

    # Get a reference to the "clk" signal on the top-level
    clk = dut.clk

    # Get a reference to a register "count"
    # in a sub-block "inst_sub_block"
    count = dut.inst_sub_block.count


Assigning values to signals
---------------------------

Values can be assigned to signals using either the
:attr:`~cocotb.handle.NonHierarchyObject.value` property of a handle object
or using direct assignment while traversing the hierarchy.

.. code-block:: python3

    # Get a reference to the "clk" signal and assign a value
    clk = dut.clk
    clk.value = 1

    # Direct assignment through the hierarchy
    dut.input_signal <= 12

    # Assign a value to a memory deep in the hierarchy
    dut.sub_block.memory.array[4] <= 2


The syntax ``sig <= new_value`` is a short form of ``sig.value = new_value``.
It not only resembles HDL-syntax, but also has the same semantics:
writes are not applied immediately, but delayed until the next write cycle.
Use ``sig.setimmediatevalue(new_val)`` to set a new value immediately
(see :meth:`~cocotb.handle.ModifiableObject.setimmediatevalue`).



Reading values from signals
---------------------------

Accessing the :attr:`~cocotb.handle.NonHierarchyObject.value` property of a handle object will return a :any:`BinaryValue` object.
Any unresolved bits are preserved and can be accessed using the :attr:`~cocotb.binary.BinaryValue.binstr` attribute,
or a resolved integer value can be accessed using the :attr:`~cocotb.binary.BinaryValue.integer` attribute.

.. code-block:: python3

    >>> # Read a value back from the DUT
    >>> count = dut.counter.value
    >>>
    >>> print(count.binstr)
    1X1010
    >>> # Resolve the value to an integer (X or Z treated as 0)
    >>> print(count.integer)
    42
    >>> # Show number of bits in a value
    >>> print(count.n_bits)
    6

We can also cast the signal handle directly to an integer:

.. code-block:: python3

    >>> print(int(dut.counter))
    42



Parallel and sequential execution of coroutines
-----------------------------------------------

.. code-block:: python3

    @cocotb.coroutine
    def reset_dut(reset_n, duration):
        reset_n <= 0
        yield Timer(duration)
        reset_n <= 1
        reset_n._log.debug("Reset complete")

    @cocotb.test()
    def parallel_example(dut):
        reset_n = dut.reset

        # This will call reset_dut sequentially
        # Execution will block until reset_dut has completed
        yield reset_dut(reset_n, 500)
        dut._log.debug("After reset")

        # Call reset_dut in parallel with this coroutine
        reset_thread = cocotb.fork(reset_dut(reset_n, 500)

        yield Timer(250)
        dut._log.debug("During reset (reset_n = %s)" % reset_n.value)

        # Wait for the other thread to complete
        yield reset_thread.join()
        dut._log.debug("After reset")
