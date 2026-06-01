********************************************
Demystifying cocotb's Build and Test Systems
********************************************

cocotb comes with multiple build systems and test regression systems, each with their own set of features.
This confusion is compounded by the fact that some tools, such as ``pytest``, interact with these systems in different ways in different contexts.
This document aims to clarify the differences between these systems and how they interact with each other.

The Makefile-based Build System
===============================

When cocotb was created, there was no existing mature open source build systems for HDL projects.
So, to get users up and running with cocotb, and to service cocotb's own internal testing needs,
a :doc:`Makefile-based build system <building>` was created.

This build system has users define their project declaratively in a Makefile,
then it handles the details of building the HDL design and running a simulation with cocotb enabled.

.. code-block:: make

   SIM = icarus
   TOPLEVEL_LANG = verilog
   VERILOG_SOURCES = $(shell pwd)/../hdl/my_design.sv
   TOPLEVEL = my_design
   include $(shell cocotb-config --makefiles)/Makefile.sim

How cocotb Simulations Work
===========================

When the Makefiles run a cocotb simulation, they invoke the simulator with an option to load a VPI, VHPI, or FLI extension module.
cocotb *is* that extension module.
This extension module, as part of its start up process, embeds a Python interpreter into the simulator process
and then loads into a series of :envvar:`Python entry points <PYGPI_USERS>`.
Chief among those is the one that starts up the :class:`!RegressionManager` test runner.

The :class:`!RegressionManager`
===============================

Now we are in a running simulation with a Python interpreter embedded and the cocotb library loaded.
We need to discover our tests, run them, and collect and report the results.
This is the responsibility of the :class:`.RegressionManager`.

The :class:`!RegressionManager` is running within the simulator process and so it must be configured with environment variables.
These environment variables are set by the Makefiles when they invoke the simulator or by ``export``\ ing user-defined Makefile variables.

.. code-block:: bash

   # tells the RegressionManager where to look for tests
   COCOTB_TEST_MODULES=test_unit,test_subsystem,test_integration
   # tells the RegressionManager the top-level module of the design
   COCOTB_TOPLEVEL=my_design
   # tells the RegressionManager which random seed to use for this test run
   COCOTB_RANDOM_SEED=12345

We will skip the details of how the :class:`!RegressionManager` discovers and runs tests in this document,
so we can focus on the differences between the various Build and Test systems.

The Python Runners
==================

There are several issues with using Makefiles as a build system:

* Not natively supported on Windows.
* Limited built-in functionality, requires shelling out.
* Shell features are not consistent between different OSes.

To address these issues and others, cocotb developed a Python-based build and test runner system known as the `Python Runners <howto-python-runner>`_.
This system does the exact same job as the Makefile-based system, but is implemented in Python.
Instead of writing a declarative Makefile, users write a Python script that uses the Python Runners API to configure and run their tests.

.. code-block:: python

    from cocotb_tools.runner import get_runner

    runner = get_runner("verilator")
    runner.build(
        hdl_toplevel="my_design",
        hdl_sources=["../hdl/my_design.sv"],
    )
    runner.test(
        test_modules=["test_unit", "test_subsystem", "test_integration"],
        random_seed=12345,
    )

After a Python Runner has built the design and started the simulation, the rest of the flow is the same as the Makefile-based system:
the :class:`!RegressionManager` discovers and runs tests in exactly the same way,
albeit with the environment variables being set according to arguments passed to the Python Runner's API.

Running with ``pytest``
-----------------------

The Python scripts that use the Python Runners to build and run cocotb tests can be written as `pytest <https://docs.pytest.org/en/stable/>`_ test functions
instead of as standalone Python scripts.
This allows users to use pytest's features in conjunction with the Python Runner build and simulation functionality.

.. code-block:: python

    import pytest
    from cocotb_tools.runner import get_runner

    # Run the build and test with different values of the build parameter "my_build_param"

    @pytest.mark.parametrize("my_build_param", [1, 2, 3])
    def test_my_design(my_build_param):
        runner = get_runner("verilator")
        runner.build(
            hdl_toplevel="my_design",
            hdl_sources=["../hdl/my_design.sv"],
            parameters={
                "my_build_param": my_build_param,
            }
        )
        runner.test(
            test_modules=["test_unit", "test_subsystem", "test_integration"],
            random_seed=12345,
        )

When ``pytest`` is used to run a Python Runner based test,
the build and test steps performed by the Python Runner are exactly the same as if the Python Runners were used directly.
``pytest`` is not integrated into the rest of the test flow in any way.

When using ``pytest`` in this manner ``pytest`` does not discover or run the cocotb tests directly,
it only discovers functions which use the Python Runners API to build and run cocotb simulations.
This means you cannot use pytest features directly on cocotb tests.

The ``pytest`` Plugin
=====================

The :doc:`pytest plugin <pytest>` is an integrated build, simulation, and test runner that supplants the :class:`!RegressionManager`
in addition to doing builds and running simulations.

In this system, ``pytest`` runs outside of the simulator process where it discovers cocotb tests directly.
It deduces what build and simulation running steps are necessary to run each cocotb tests.
Then it uses the Python Runners to build and run the simulations necessary for each cocotb test.

This means that you can use pytest features directly on cocotb tests.
For example, parametrizing tests with :ref:`@pytest.mark.parametrize <@pytest.mark.parametrize>`
and marking tests as expected to fail with :any:`@pytest.mark.xfail <pytest.mark.xfail>`.

.. note:: The ``pytest`` plugin is still in development and is not yet recommended for general use.
