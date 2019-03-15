################
Quickstart Guide
################


Installing cocotb
=================

Pre-requisites
--------------

Cocotb has the following requirements:

* Python 2.7+
* Python-dev packages
* GCC and associated development packages
* GNU Make
* A Verilog or VHDL simulator, depending on your source RTL code

Internal development is performed on Linux Mint 17 (x64). We also use RedHat
6.5(x64). Other RedHat and Ubuntu based distributions (x32 and x64) should work
too but due fragmented nature of Linux we can not test everything. Instructions
are provided for the main distributions we use.

Linux native arch installation
------------------------------

Ubuntu based installation

.. code-block:: bash

    $> sudo apt-get install git make gcc g++ swig python-dev

This will allow building of the cocotb libs for use with a 64-bit native
simulator. If a 32-bit simulator is being used then additional steps to install
32-bit development libraries and Python are needed. 

RedHat based installation

.. code-block:: bash

    $> sudo yum install gcc gcc-c++ libstdc++-devel swig python-devel

This will allow building of the cocotb libs for use with a 64-bit native
simulator. If a 32-bit simulator is being used then additional steps to install
32-bit development libraries and Python are needed. 


32-bit Python
-------------

Additional development libraries are needed for building 32-bit Python on 64-bit
systems.

Ubuntu based installation

.. code-block:: bash

    $> sudo apt-get install libx32gcc1 gcc-4.8-multilib lib32stdc++-4.8-dev

Replace 4.8 with the version of GCC that was installed on the system in the step
above. Unlike on RedHat where 32-bit Python can co-exist with native Python,
Ubuntu requires the source to be downloaded and built.

RedHat based installation

.. code-block:: bash

    $> sudo yum install glibc.i686 glibc-devel.i386 libgcc.i686 libstdc++-devel.i686


Specific releases can be downloaded from https://www.python.org/downloads/ .

.. code-block:: bash

    $> wget https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz
    $> tar xvf Python-2.7.9.tgz
    $> cd Python-2.7.9
    $> export PY32_DIR=/opt/pym32
    $> ./configure CC="gcc -m32" LDFLAGS="-L/lib32 -L/usr/lib32 -Lpwd/lib32 -Wl,-rpath,/lib32 -Wl,-rpath,$PY32_DIR/lib" --prefix=$PY32_DIR --enable-shared
    $> make
    $> sudo make install

Cocotb can now be built against 32-bit Python by setting the architecture and
placing the 32-bit Python ahead of the native version in the path when running a
test.

.. code-block:: bash

    $> export PATH=/opt/pym32/bin
    $> cd <cocotb_dir>
    $> ARCH=i686 make

Windows 7 installation
----------------------

Work has been done with the support of the cocotb community to enable
Windows support using the MinGW/Msys environment. Download the MinGQ installer
from.

https://sourceforge.net/projects/mingw/files/latest/download?source=files .

Run the GUI installer and specify a directory you would like the environment
installed in. The installer will retrieve a list of possible packages, when this
is done press continue. The MinGW Installation Manager is then launched.

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

Python can be downloaded from https://www.python.org/ftp/python/2.7.9/python-2.7.9.msi,
other versions of Python can be used as well. Run the installer and download to
your chosen location.

It is beneficial to add the path to Python to the Windows system ``PATH`` variable
so it can be used easily from inside Msys.

Once inside the Msys shell commands as given here will work as expected.

macOS Packages
--------------

You need a few packages installed to get cocotb running on macOS.
Installing a package manager really helps things out here.

`Brew <https://brew.sh/>`_ seems to be the most popular, so we'll assume you have that installed.

.. code-block::bash
    
    $> brew install python icarus-verilog gtkwave
    
Running an example
------------------

.. code-block:: bash

    $> git clone https://github.com/potentialventures/cocotb
    $> cd cocotb/examples/endian_swapper/tests
    $> make

To run a test using a different simulator:

.. code-block:: bash

    $> make SIM=vcs


Running a VHDL example
----------------------

The ``endian_swapper`` example includes both a VHDL and a Verilog RTL implementation.
The cocotb testbench can execute against either implementation using VPI for
Verilog and VHPI/FLI for VHDL.  To run the test suite against the VHDL
implementation use the following command (a VHPI or FLI capable simulator must
be used):

.. code-block:: bash

    $> make SIM=ghdl TOPLEVEL_LANG=vhdl


Using cocotb
============

A typical cocotb testbench requires no additional RTL code.
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

.. code-block:: bash

    VERILOG_SOURCES = $(PWD)/submodule.sv $(PWD)/my_design.sv
    TOPLEVEL=my_design  # the module name in your Verilog or VHDL file
    MODULE=test_my_design  # the name of the Python test file
    include $(COCOTB)/makefiles/Makefile.inc
    include $(COCOTB)/makefiles/Makefile.sim

We would then create a file called ``test_my_design.py`` containing our tests.


Creating a test
---------------

The test is written in Python. Cocotb wraps your top level with the handle you
pass it. In this documentation, and most of the examples in the project, that
handle is ``dut``, but you can pass your own preferred name in instead. The
handle is used in all Python files referencing your RTL project. Assuming we
have a toplevel port called ``clk`` we could create a test file containing the
following:

.. code-block:: python

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

.. code-block:: python

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

.. code-block:: python
    
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

.. code-block:: python
    
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

.. code-block:: python

    >>> print(int(dut.counter))
    42



Parallel and sequential execution of coroutines
-----------------------------------------------

.. code-block:: python

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

