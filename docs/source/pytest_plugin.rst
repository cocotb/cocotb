.. _pytest-plugin:

*************
Pytest Plugin
*************

.. warning::
    The pytest plugin is under active development, and the API **will** change in breaking ways over the next release or two.

    You can still use pytest with the :ref:`Python runners <runner-with-pytest>` for building designs and running simulations.
    You can also use pytest features in cocotb tests, such as :func:`pytest.raises`, :func:`pytest.skip`, or pytest's assertion rewriting.

The :mod:`cocotb_tools.pytest.plugin` module provides full `pytest`_ integration with cocotb, including:

* `fixtures`_: Cleanly set up and tear down cocotb tests and designs under test (DUTs).
* `plugins`_: Extend cocotb testing capabilities.
* `configuration`_: Configure the cocotb testing environment using :ref:`command line arguments <pytest-plugin-options>` (``--cocotb-*``),
  configuration files like `pyproject.toml`_ or `fixture`_ arguments for fine-grained control per test, class, module, or session.
* Discovery: List all available cocotb tests and their relationship with simulations.
* `marks`_: Easily associate metadata with cocotb test functions.
* Filtering: Filter cocotb tests using `pytest`_ ``-k '<expression>'`` and ``-m '<markers>'`` options.
* Reporting: Report all executed cocotb tests.
* Parallel execution: Run simulations with cocotb tests in parallel by using the `pytest-xdist`_ plugin.


.. _pytest-plugin-enable:

Enabling the Plugin
===================

The :mod:`cocotb_tools.pytest.plugin` can be enabled in several ways depending on your project type.

In a Python Project
-------------------

When using a `pyproject.toml`_ file (the recommended way):

.. code:: toml

    [project.entry-points.pytest11]
    cocotb = "cocotb_tools.pytest.plugin"

When using a ``pytest.ini`` file:

.. code:: ini

    [pytest]
    addopts = -p cocotb_tools.pytest.plugin

When using a ``setup.cfg`` file:

.. code:: ini

    [options.entry_points]
    pytest11 =
      cocotb = cocotb_tools.pytest.plugin

When using a ``setup.py`` file:

.. code:: python

    from setuptools import setup

    setup(
        # ...,
        entry_points={
            "pytest11": [
                "cocotb = cocotb_tools.pytest.plugin",
            ],
        },
    )

In a Non-Python Project
-----------------------

If your project is not structured as a standard Python package, you can enable the plugin in one of the following ways:

* By defining the global variable ``pytest_plugins`` in a ``conftest.py`` file located in the project root:

  .. code:: python

      pytest_plugins = ("cocotb_tools.pytest.plugin",)

* By defining the ``PYTEST_PLUGINS`` environment variable:

  .. code:: shell

      export PYTEST_PLUGINS="cocotb_tools.pytest.plugin"

* By passing the ``-p <plugin>`` option when invoking the `pytest`_ command-line interface:

  .. code:: shell

      pytest -p cocotb_tools.pytest.plugin ...


.. _pytest-plugin-build-and-test:

Building and Testing
====================

The pytest plugin compiles HDL designs and runs simulations.
To do this, it needs configuration details about the HDL design, such as the list of source files, defines, parameters and the simulator to use.
The :class:`cocotb_tools.pytest.dut.Dut` class represents the Design Under Test (DUT) and carries all of this configuration.

How it works:

1. Pytest `fixtures`_ are defined to return a :class:`~cocotb_tools.pytest.dut.Dut` object.
2. The plugin initially configures this :class:`~cocotb_tools.pytest.dut.Dut` object using the command-line arguments (``--cocotb-*``),
   configuration files (such as `pyproject.toml`_), and any :ref:`@pytest.mark.cocotb_* <api-pytest-plugin-markers>` markers applied to the test.
3. You can further customize the :class:`~cocotb_tools.pytest.dut.Dut` object in your fixture.
4. When pytest executes the test, the plugin invokes the :meth:`cocotb_tools.pytest.dut.Dut.run` method.
5. This method delegates compiling the HDL design and running the simulation to the :func:`~cocotb_tools.pytest.hookspecs.pytest_cocotb_dut_run` hook.
   The default implementation of this hook uses the :ref:`Python runners <howto-python-runner>`.


.. _pytest-plugin-fixtures:

Fixtures
--------

To define a custom DUT configuration, you create a pytest fixture.
The plugin identifies fixtures that return a DUT configuration by inspecting their return type annotation.

To ensure your fixture is correctly recognized, it must meet the following rules:

* It must be a normal Python function (do **not** define it as a coroutine function using the ``async def`` keyword).
* Its return type must be annotated with the :class:`~cocotb_tools.pytest.dut.Dut` type, (for example, ``-> Dut:`` or ``-> Generator[Dut]:``).

An example is provided below.
This fixture can be placed in a ``conftest.py`` file (to share it across multiple test files) or directly in a ``test_*.py`` file:

.. code:: python

    # conftest.py or test_*.py file
    from pathlib import Path
    from pytest import FixtureRequest, fixture
    from cocotb_tools.pytest.dut import Dut

    # Path to the directory containing RTL source files
    RTL_DIR = Path(__file__).parent.parent.resolve() / "rtl"

    @fixture
    def sample_module(request: FixtureRequest) -> Dut:
        """Define the HDL design under test and specify its source files.

        Args:
            request: The pytest fixture request used by the plugin to initialize
                     the Dut instance with configuration from command line arguments,
                     configuration files, and markers.

        Returns:
            The Dut object containing the design configuration.
        """
        # Create the Dut configuration object using the pytest request context
        dut = Dut(request)

        # Add the HDL source files to compile
        dut.sources += [
            RTL_DIR / "sample_module.sv",
        ]

        return dut

This defined fixture can be later referenced in a test:

.. code:: python

    # test_*.py

    async def test_feature_1(sample_module) -> None:
        """Test design feature 1 of the sample module."""
        sample_module.i_data.value = 10
        assert sample_module.o_data.value == 10

.. important::
    Notice how ``sample_module`` behaves in the test function above.
    Inside the test coroutine, which runs inside the simulator process,
    the ``sample_module`` argument is automatically resolved to the actual simulator handle for the DUT.
    It is **not** the :class:`~cocotb_tools.pytest.dut.Dut` configuration object.
    This means you can drive and read signals on it directly (e.g. ``sample_module.i_data.value = 10``), exactly like :data:`cocotb.top`.


:fixture:`~cocotb_tools.pytest.plugin.dut`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plugin provides a built-in :fixture:`~cocotb_tools.pytest.plugin.dut` fixture.
You can use it directly in your tests if you do not need custom fixture logic,
or you can inject it into your custom fixtures to build on top of it.

For example, you can inject the built-in ``dut`` fixture into your own fixture to avoid having to instantiate :class:`~cocotb_tools.pytest.dut.Dut` manually using the ``request`` object:

.. code:: python

    # conftest.py or test_*.py file
    from pathlib import Path
    from pytest import fixture
    from cocotb_tools.pytest.dut import Dut

    # Path to the directory containing RTL source files
    RTL_DIR = Path(__file__).parent.parent.resolve() / "rtl"

    @fixture
    def sample_module(dut: Dut) -> Dut:
        """Define a custom DUT configuration using the built-in dut fixture.

        Args:
            dut: The built-in fixture carrying the default DUT configuration.

        Returns:
            The customized Dut configuration.
        """
        dut.sources += [
            RTL_DIR / "sample_module.sv",
        ]

        return dut


.. _pytest-plugin-markers:

Using Markers
-------------

You can use pytest markers to configure the DUT on a per-test or per-module basis.
Markers starting with ``@pytest.mark.cocotb_*`` allow you to override settings like sources, timescales, parameters or simulation arguments.

* **Module-level configuration**:
  Define a global ``pytestmark`` variable in your test module.
  This applies the markers to all test functions in the file.
* **Test-level configuration**:
  Apply markers directly to a specific test coroutine.

Here is an example:

.. code:: python

    # test_*.py
    from pathlib import Path
    import pytest

    # Path to the directory containing RTL source files
    RTL_DIR = Path(__file__).parent.parent.resolve() / "rtl"

    # Apply marks to all tests in this module
    pytestmark = (
        pytest.mark.cocotb_sources(RTL_DIR / "sample_module.sv"),
    )

    async def test_feature_1(dut) -> None:
        """Uses the global module-level source setting."""
        dut.i_data.value = 10
        ...

    # Apply a custom timescale to only this test function
    @pytest.mark.cocotb_timescale("1ns/1ps")
    async def test_feature_2_with_timescale(dut) -> None:
        """Uses the custom timescale configured specifically for this test."""
        ...


.. _pytest-plugin-toplevel:

Toplevel Module Name Inference
------------------------------

The simulator needs to know the name of the HDL toplevel module to run the simulation.
If you do not explicitly set the :attr:`cocotb_tools.pytest.dut.Dut.toplevel` attribute,
and do not use the :deco:`!pytest.mark.cocotb_toplevel` marker,
the plugin will automatically infer the toplevel module name using the following order of precedence:

1. **Last added source file**:
   The base name of the last file added to :attr:`cocotb_tools.pytest.dut.Dut.sources`, excluding the file extension.
   For example, if the last added source is ``RTL_DIR / "design.sv"``, the toplevel name is assumed to be ``design``.
2. **First test module name**:
   The name of the first Python test module in :attr:`cocotb_tools.pytest.dut.Dut.test_modules`,
   with any ``test_`` prefix or ``_test`` suffix stripped.
   For example, if the test module is named ``test_alu.py``, the toplevel name is assumed to be ``alu``.

An example showing automatic inference:

.. code:: python

    # conftest.py
    from pathlib import Path
    from pytest import fixture
    from cocotb_tools.pytest.dut import Dut

    # Path to the directory containing RTL source files
    RTL_DIR = Path(__file__).parent.parent.resolve() / "rtl"

    @fixture
    def sample_module(dut: Dut) -> Dut:
        dut.sources += [
            RTL_DIR / "sample_module.sv",
        ]

        # The toplevel attribute is automatically set to "sample_module"
        assert dut.toplevel == "sample_module"

        return dut


.. _pytest-plugin-test-modules:

Test Modules
------------

A test module is a Python file (such as ``test_sample_module.py``) containing cocotb tests.

By default, if the :attr:`cocotb_tools.pytest.dut.Dut.test_modules` list is not set explicitly,
and the :deco:`!pytest.mark.cocotb_test_modules` marker is not used,
the plugin defaults to running cocotb tests defined in the current Python module where the test is being executed.

An example:

.. code:: python

    # test_sample_module.py
    from pytest import fixture
    from cocotb_tools.pytest.dut import Dut

    @fixture
    def sample_module(dut: Dut) -> Dut:
        # The plugin automatically associates this module name
        assert dut.test_modules == ["test_sample_module"]

        return dut


.. _pytest-plugin-test-functions:

Test Functions
--------------

The plugin automatically discovers your cocotb tests.
A function is recognized as a cocotb test if it meets the following criteria:

* Its name starts with the ``test_`` prefix.
* It is defined as a coroutine function using the ``async def`` keyword.

For example:

.. code:: python

    async def test_feature_1(dut) -> None:
        """Test design feature 1."""
        # Test implementation
        ...

Referencing a custom :class:`~cocotb_tools.pytest.dut.Dut` fixture is optional.
If your test function does not specify any custom DUT fixture,
the plugin automatically associates it with the default, built-in :fixture:`~cocotb_tools.pytest.plugin.dut` fixture.

.. note::

   The plugin also recognizes test functions decorated with standard cocotb decorators such as :deco:`cocotb.test`,
   :deco:`cocotb.parametrize`, :deco:`cocotb.skipif` or :deco:`cocotb.xfail`.
   When using these decorators, the function name does not need to start with the ``test_`` prefix.


.. _pytest-plugin-work-directory:

Work Directory
--------------

The work directory is the location where the simulator compiles, elaborates, and runs the design.
The plugin guarantees that this directory is unique for each distinct :class:`~cocotb_tools.pytest.dut.Dut` configuration.

The path is constructed using the properties of the :class:`~cocotb_tools.pytest.dut.Dut` instance as follows:

.. code:: text

   <dut.build_dir>/<dut.toplevel_library>/<dut.toplevel>/<dut.parameters>/<dut.id>

Where ``<dut.parameters>`` is a string representing the key-value pairs of the design parameters/generics,
and ``<dut.id>`` is a unique hash of the configuration settings.

Example:

.. code:: text

   build_sim/top/alu/WIDTH_8/d75117a510e1020e864f36822f96eeb8b9427534


.. _pytest-plugin-parametrize-dut:

Parametrizing Dut Instances
---------------------------

In hardware verification, it is common to test a design with different configurations - such as varying data bus widths, buffer sizes, or clock periods.
Parametrizing your simulations allows you to run the same set of testcases across all these design variations without duplicating code.

With the pytest plugin, you can easily parametrize your :class:`~cocotb_tools.pytest.dut.Dut` instances using pytest's standard :ref:`@pytest.mark.parametrize <parametrize>` decorator.

How it Works
^^^^^^^^^^^^

The recommended way to parametrize a DUT parameter (or generic) is to:

1. **Define a default parameter fixture**. This fixture returns the default value used when no parametrization is specified.
2. **Define a DUT fixture with parameter fixture(s)**. In this fixture,
   request parameter fixture(s) and assign its value(s) to the :class:`~cocotb_tools.pytest.dut.Dut` configuration object.
3. **Use the @pytest.mark.parametrize decorator** on your test functions to override the parameter value for specific test runs.

Let's look at a complete example:

.. code:: python

    # conftest.py or test_*.py
    import pytest
    from pytest import fixture
    from cocotb_tools.pytest.dut import Dut

    @fixture
    def WIDTH() -> int:
        """The default value of the Dut WIDTH parameter."""
        return 8

    @fixture(name="dut")
    def dut_fixture(dut: Dut, WIDTH: int) -> Dut:
        """Parametrize the Dut WIDTH parameter."""
        dut["WIDTH"] = WIDTH

        return dut

    async def test_feature_1(dut) -> None:
        """Test design feature 1 without parametrization."""
        ...

    @pytest.mark.parametrize("WIDTH", (1, 2, 4))
    async def test_feature_1_with_parametrized_width(dut) -> None:
        """Test design feature 1 with different value of the Dut WIDTH parameter."""
        ...

    @pytest.mark.parametrize("WIDTH", (8, 16))
    @pytest.mark.parametrize("value", (1, 2))
    async def test_feature_1_with_parametrized_width_and_value(dut, value: int) -> None:
        """Test design feature 1 with different value of the Dut WIDTH parameter."""
        dut.stream_in_data.value = value

Indirect Parametrization Explained
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here is what is happening under the hood:

1. When pytest discovers a test function like ``test_feature_1_with_parametrized_width``,
   it sees that the test requests the ``dut`` fixture and specifies a parameter named ``WIDTH``.
2. Pytest notices that the ``dut_fixture`` itself depends on the ``WIDTH`` fixture.
3. Because ``WIDTH`` is parametrized on the test function, pytest overrides the default ``WIDTH`` fixture with each of the parametrized values (``1``, ``2``, and ``4``).
4. For each parameter value, pytest:

   * Re-evaluates the ``WIDTH`` fixture with that value.
   * Invokes the ``dut_fixture``, which retrieves the current ``WIDTH`` value and sets it on the ``dut`` object (``dut["WIDTH"] = WIDTH``).

Simulation Isolation and Caching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because the plugin automatically includes design parameters in the build directory path (see :ref:`pytest-plugin-work-directory`),
pytest runs each parametrized simulation in a separate, isolated directory.

For example, when running the tests above, the build directories will look similar to::

    build_sim/
    └── library/
        └── top/
            ├── WIDTH_1/
            ├── WIDTH_2/
            ├── WIDTH_4/
            ├── WIDTH_8/
            └── WIDTH_16/

This isolation ensures that simulations with different parameters do not interfere with or overwrite one another and compile outputs can be safely cached, reused and even executed in parallel (for example with the `pytest-xdist`_ plugin).


.. _pytest-plugin-test-discovery:

Test Discovery and Filtering
============================

You can list all discovered tests, simulations and their hierarchy by invoking `pytest`_ with the ``--collect-only`` flag:

.. code:: shell

   pytest --collect-only

Example collection output:

.. code:: text

    <Cocotb>
      <Dut library.sample_module[WIDTH=8]>
        <Function simulation>
        <TestModule test_sample_module>
          <Function test_feature_1>
          <Function test_feature_2[2-4-8]>
          <Function test_feature_3[4-8-16]>

Hierarchy node details:

* **Cocotb**: The collection of all discovered cocotb environments.
* **Dut**: Represents a configured :class:`~cocotb_tools.pytest.dut.Dut` environment (for example ``library.sample_module[WIDTH=8]``).
* **Function simulation**: An internal function generated by the plugin to build the HDL design and launch the simulation.
* **TestModule**: A discovered Python module containing cocotb tests.
* **Function test_***: Individual cocotb tests that will run within that simulation.

Filtering Tests
---------------

You can filter and run specific test suites or individual tests using standard pytest options:

* **Filter by name**:
  Use the ``-k`` option to run tests matching a specific pattern:

  .. code:: shell

     pytest -k "test_sample_module and test_feature_2"

* **Filter by marker**:
  Use the ``-m`` option to select tests containing specific markers:

  .. code:: shell

     pytest -m "cocotb"


.. _pytest-plugin-user-fixtures:

Writing Custom Pytest Fixtures
==============================

You can write custom ``pytest`` fixtures to automate common tasks in your cocotb testbenches.
These fixtures run inside the simulation process and must be defined as coroutines using the ``async def`` keyword.
They can inject other fixtures (like the DUT handle ``dut``) and support standard pytest setups,
teardowns (using the ``yield`` keyword), and scopes.

Common Patterns and Examples
----------------------------

1. **Automatic Clock Generation**
   A session-scoped fixture can start a clock that runs throughout the entire simulation session across all tests:

   .. code:: python

       # conftest.py or test_*.py
       from collections.abc import AsyncGenerator
       import pytest
       from cocotb.clock import Clock

       @pytest.fixture(scope="session", autouse=True)
       async def clock_generation(dut) -> AsyncGenerator[None, None]:
           """Automatically generate a clock for all tests."""
           # Setup: Initialize the clock signal and start the clock generator
           dut.clk.value = 0
           clock = Clock(dut.clk, 10, unit="ns")
           clock.start(start_high=False)

           yield  # The tests run here

           # Teardown: Executed after all tests are finished

2. **DUT Reset and Initialization**
   A function-scoped fixture (the default scope) can reset the DUT and initialize signals before each test,
   and clean up afterwards:

   .. code:: python

       # conftest.py or test_*.py
       from collections.abc import AsyncGenerator
       import pytest
       from cocotb.triggers import FallingEdge

       @pytest.fixture(autouse=True)
       async def setup_dut(dut) -> AsyncGenerator[None, None]:
           """Reset the DUT before each test and clear signals on teardown."""
           # Setup: Assert reset and initialize input signals
           dut.rst.value = 1
           dut.stream_in_valid.value = 0
           dut.stream_in_data.value = 0

           # Wait for 2 clock cycles
           for _ in range(2):
               await FallingEdge(dut.clk)

           dut.rst.value = 0  # Release reset

           yield  # Run the test

           # Teardown: Clear input signals after the test finishes
           dut.stream_in_valid.value = 0
           dut.stream_in_data.value = 0

3. **Helper Drivers and Monitors**
   You can package testbench components (like bus drivers, transaction monitors, or protocol checkers) into fixtures,
   to avoid repetitive boilerplate code in your test functions:

   .. code:: python

       # conftest.py or test_*.py
       import pytest
       from cocotb.triggers import FallingEdge

       class StreamDriver:
           def __init__(self, dut):
               self.dut = dut

           async def send(self, val: int) -> None:
               self.dut.stream_in_data.value = val
               self.dut.stream_in_valid.value = 1
               await FallingEdge(self.dut.clk)
               self.dut.stream_in_valid.value = 0

       @pytest.fixture
       async def driver(dut) -> StreamDriver:
           """Create and return a StreamDriver instance."""
           return StreamDriver(dut)

       # The test receives the driver fixture and uses it directly
       async def test_stream_transfer(driver) -> None:
           await driver.send(100)
           await driver.send(200)


.. _pytest-plugin-integration:

Custom Flows and Integration
============================

If you need to integrate cocotb with an existing build flow or a custom build system, refer to :ref:`custom-flows` for general principles.

For the :mod:`cocotb_tools.pytest.plugin` pytest plugin,
the recommended way to customize the compile and run steps is by implementing the custom hooks defined in :mod:`cocotb_tools.pytest.hookspecs`.

The two main hooks you can implement are:

* :func:`~cocotb_tools.pytest.hookspecs.pytest_cocotb_dut_create`: Instantiates the :class:`~cocotb_tools.pytest.dut.Dut` class,
  (allowing you to use a custom subclass or change default settings).
* :func:`~cocotb_tools.pytest.hookspecs.pytest_cocotb_dut_run`: Customizes the build and run processes.

Example: Using a Custom Makefile
--------------------------------

Here is an example showing how to intercept the run process using a custom Makefile-based flow.
Add this hook implementation to your ``conftest.py`` file:

.. code:: python

    # conftest.py
    from subprocess import run
    from pytest import hookimpl
    from cocotb_tools.pytest.dut import Dut

    @hookimpl(tryfirst=True)
    def pytest_cocotb_dut_run(dut: Dut) -> object:
        """Compile the HDL design and run the simulation using a Makefile."""
        args: list[str] = [
            "make",
            "run",
            f"SIM={dut.simulator}",
            f"TOPLEVEL={dut.toplevel}",
            f"TOPLEVEL_LANG={dut.toplevel_lang}",
            f"TOPLEVEL_LIBRARY={dut.toplevel_library}",
            f"TEST_MODULES={','.join(dut.test_modules)}",
            f"SOURCES={','.join(map(str, dut.sources))}",
        ]

        run(args, check=True)

        # Returning True stops pytest from invoking other hook implementations
        return True

Distributing Hook Implementations
---------------------------------

If you want to share your hook implementations across multiple projects,
you can package them as a pytest plugin and publish it to the PyPI registry.
For more information, see the official pytest guide on `writing plugins <https://docs.pytest.org/en/stable/how-to/writing_plugins.html>`_.

By convention, you should prefix the name of your published Python package with ``pytest-cocotb-``.
This allows it to be automatically discovered in the list of available pytest `plugins`_.


.. _pytest-plugin-configuration:

Configuration Priority
======================

The plugin allows you to configure the cocotb environment through multiple sources.
If a configuration option is specified in multiple places,
the plugin resolves conflicts using the following order of precedence (from highest priority to lowest):

1. Attributes set directly on the :class:`~cocotb_tools.pytest.dut.Dut` object inside a fixture.
2. :ref:`@pytest.mark.cocotb_* <api-pytest-plugin-markers>` markers applied to test modules or functions.
3. ``--cocotb-*`` command-line arguments.
4. ``cocotb_*`` settings defined in configuration files such as ``pyproject.toml`` or ``pytest.ini``.
5. ``COCOTB_*`` environment variables.
6. Default values.

To list all available command-line arguments, configuration entries, and environment variables supported by the plugin, run:

.. code:: shell

    pytest --help


.. _pytest-plugin-junit-xml:

JUnit XML Reporting
===================

cocotb automatically generates a JUnit XML test report for every regression.
For detailed information on the XML schema and general behavior, see :ref:`junit` and :ref:`junit-reference`.
The plugin-specific configuration details are described below.

Specifying the Output File
--------------------------

To specify the name and location of the generated JUnit XML report,
use pytest's standard ``--junit-xml`` command-line option:

.. code:: shell

    pytest --junit-xml=junit.xml

Adding Log Attachments
----------------------

To include logs as :ref:`attachments <junit-attachments>` in your JUnit XML report,
you must configure the pytest ``junit_logging`` option to either ``system-out`` or ``all``.
This can be set in your configuration file or passed on the command line:

.. code:: shell

    pytest --override-ini=junit_logging=system-out --junit-xml=junit.xml ...


.. _pytest-plugin-under-the-hood:

Under the Hood
==============

.. image:: diagrams/svg/pytest_plugin_overview.svg


The :mod:`cocotb_tools.pytest.plugin` plugin is divided into two independent, complementary components.

1. The Parent Process (Command-Line Environment)
-------------------------------------------------

When you run ``pytest`` from the command line,
the parent pytest process starts in a non-simulation environment and performs the following tasks:

* Discovers and marks coroutine test functions as cocotb tests.
* Extracts :class:`~cocotb_tools.pytest.dut.Dut` configuration fixtures associated with those tests.
* For each unique :class:`~cocotb_tools.pytest.dut.Dut` configuration,
  implicitly creates a ``simulation`` item that invokes the :func:`~cocotb_tools.pytest.hookspecs.pytest_cocotb_dut_run` hook.
  This compiles the HDL design and launches the simulator.
* Listens for and collects serialized test reports sent by the simulation process via Inter-Process Communication (IPC).

.. note::

   The implicitly created ``simulation`` item is treated by pytest as a standard test.
   It appears in the pytest test summary, which allows compiling, elaboration, and simulation runs to be timed and reported.

2. The Child Process (Simulation Environment)
---------------------------------------------

The second component of the plugin runs directly within the simulator process.
It performs the following tasks:

* Gathers only the cocotb tests targeted for the current simulation run.
* Intercepts and replaces the :class:`~cocotb_tools.pytest.dut.Dut` fixtures to return the actual simulation top-level handle (equivalent to :data:`cocotb.top`).
* Manages asynchronous execution for pytest fixtures, test setups, test calls and test teardowns.
* Serializes individual test results and transmits them back to the parent process via IPC.


.. _pytest-plugin-migration:

Migration Guide
===============

Migrating from Manual Python Runners
------------------------------------

If you have an existing codebase that runs cocotb tests by calling the :ref:`Python runners <runner-with-pytest>` inside standard pytest functions,
you can adopt the pytest plugin incrementally.

Step 1: Run with User Runners Enabled
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can continue using your existing runner-based tests by passing the ``--cocotb-with-user-runners`` option.
This disables the plugin's automatic simulation generation, preventing duplicate runs:

.. code:: shell

   pytest --cocotb-with-user-runners

Alternatively, you can configure this in your ``pyproject.toml`` file:

.. code:: toml

    [tool.pytest]
    cocotb_with_user_runners = true

Step 2: Verify the Regression Manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, pytest acts as the regression manager for the cocotb tests.
If you need to fall back to cocotb's built-in regression manager, use the following option:

.. code:: shell

   pytest --cocotb-regression-manager=cocotb

Step 3: Convert Runners to DUT Fixtures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once you verify that the tests run successfully, you can migrate to the native plugin structure.
This involves replacing the manual runner builder code with a :class:`~cocotb_tools.pytest.dut.Dut` fixture or markers.

For example, if you have a runner-based test like this:

.. code:: python

    # test_sample_module.py (Before Migration)
    import os
    from pathlib import Path

    import cocotb
    from cocotb_tools.runner import get_runner

    RTL_DIR = Path(__file__).parent.parent.resolve() / "rtl"

    def test_sample_module() -> None:
        runner = get_runner(os.environ.get("SIM", "icarus"))
        sources = [RTL_DIR / "sample_module.sv"]

        runner.build(
            sources=sources,
            hdl_toplevel="sample_module",
        )

        runner.test(
            test_module="test_sample_module",
            hdl_toplevel="sample_module",
        )

    @cocotb.test
    async def test_feature_1(dut) -> None:
        """Test design feature 1."""
        ...

You can refactor it to use a custom ``dut`` fixture:

.. code:: python

    # test_sample_module.py (After Migration using Fixtures)
    from pathlib import Path
    from pytest import fixture
    from cocotb_tools.pytest.dut import Dut

    RTL_DIR = Path(__file__).parent.parent.resolve() / "rtl"

    @fixture(name="dut")
    def dut_fixture(dut: Dut) -> Dut:
        dut.sources += [RTL_DIR / "sample_module.sv"]
        return dut

    # The @cocotb.test decorator is no longer required and can be removed
    async def test_feature_1(dut) -> None:
        """Test design feature 1."""
        ...

Alternatively, you can use module-level markers for a zero-boilerplate configuration:

.. code:: python

    # test_sample_module.py (After Migration using Markers)
    from pathlib import Path
    import pytest

    RTL_DIR = Path(__file__).parent.parent.resolve() / "rtl"

    pytestmark = (
        pytest.mark.cocotb_sources(RTL_DIR / "sample_module.sv"),
    )

    async def test_feature_1(dut) -> None:
        """Test design feature 1."""
        ...


.. _pytest-plugin-options:

Options
=======

.. argparse::
   :module: cocotb_tools.pytest.plugin
   :func: _options_for_documentation
   :prog: pytest
   :nodefault:

.. _pytest: https://docs.pytest.org/en/stable/contents.html
.. _fixture: https://docs.pytest.org/en/stable/explanation/fixtures.html#about-fixtures
.. _fixtures: https://docs.pytest.org/en/stable/explanation/fixtures.html#about-fixtures
.. _plugins: https://docs.pytest.org/en/stable/reference/plugin_list.html#plugin-list
.. _configuration: https://docs.pytest.org/en/stable/reference/customize.html
.. _pyproject.toml: https://packaging.python.org/en/latest/specifications/pyproject-toml/
.. _marks: https://docs.pytest.org/en/stable/how-to/mark.html
.. _pytest-xdist: https://github.com/pytest-dev/pytest-xdist
.. _parametrize: https://docs.pytest.org/en/stable/example/parametrize.html
