.. _pytest-support:

**************
Pytest Support
**************

:py:mod:`cocotb_tools.pytest.plugin` provides full `pytest`_ integration with cocotb. Including:

* `fixtures`_ to cleanly set up and tear down cocotb tests and designs under test.
* `plugins`_ that can extend cocotb testing capabilities.
* `configuration`_ facilities to configure the cocotb testing environment using
  :ref:`command line arguments <pytest-plugin-options>` ``--cocotb-*``,
  configuration files like `pyproject.toml`_ or `fixture`_ arguments for fine control per test, class, module or session.
* listing all available cocotb tests and their relationship with :py:mod:`cocotb_tools.runner`.
* `marks`_ to easily set metadata on cocotb test functions.
* filtering cocotb tests with `pytest`_ ``-k '<expression>'`` and ``-m '<markers>'`` options.
* reporting all executed cocotb tests.
* parallel execution of cocotb runners by using the `pytest-xdist`_ plugin

Enabling the Plugin
===================

:py:mod:`cocotb_tools.pytest.plugin` can be enabled in various ways.

In a Python project
-------------------

When using the `pyproject.toml`_ file (recommended way):

.. code:: toml

    [project.entry-points.pytest11]
    cocotb = "cocotb_tools.pytest.plugin"

When using the ``pytest.ini`` file:

.. code:: ini

    [pytest]
    addopts = -p cocotb_tools.pytest.plugin

When using the ``setup.cfg`` file:

.. code:: ini

    [options.entry_points]
    pytest11 =
      cocotb = cocotb_tools.pytest.plugin

When using the ``setup.py`` file:

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

In a non-Python project
-----------------------

By defining the global variable ``pytest_plugins`` when using a ``conftest.py`` file
(which must be located in the root of the project):

.. code:: python

    pytest_plugins = ("cocotb_tools.pytest.plugin",)

By defining the ``PYTEST_PLUGINS`` environment variable:

.. code:: shell

    export PYTEST_PLUGINS="cocotb_tools.pytest.plugin"

By using the ``-p <plugin>`` option when invoking the `pytest`_ command line interface:

.. code:: shell

    pytest -p cocotb_tools.pytest.plugin ...


.. _pytest-plugin-build-and-test:

Building and Testing
====================

:py:class:`cocotb_tools.pytest.hdl.HDL` interfaces with the :ref:`Python runners <howto-python-runner>` to build designs and run simulations.
The :py:class:`~cocotb_tools.runner.Runner` is fully configurable by using ``--cocotb-*`` command line arguments,
configuration files like `pyproject.toml`_ or `fixture`_ arguments.


.. _pytest-plugin-fixtures:

Fixtures
--------

:py:fixture:`cocotb_tools.pytest.plugin.hdl`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plugin provides an :fixture:`~cocotb_tools.pytest.plugin.hdl` fixture that will create a new instance of
:py:class:`~cocotb_tools.pytest.hdl.HDL` that can be customized and then used in tests.

An example is provided below, located in a project ``conftest.py`` file:

.. code:: python

    import pytest
    from cocotb_tools.pytest.hdl import HDL


    @pytest.fixture(name="sample_module")
    def sample_module_fixture(hdl: HDL) -> HDL:
        """Define HDL design by adding HDL source files to it.

        Args:
            hdl: Fixture created by the cocotb pytest plugin, representing a HDL design.

        Returns:
            Representation of HDL design with added HDL source files.
        """
        hdl.sources = (
            # List HDL source files,
            "sample_module.sv",
        )

        # Build HDL design
        hdl.build()

        return hdl


.. _pytest-plugin-markers:

Markers
-------

:py:deco:`!pytest.mark.cocotb_runner`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plugin provides the marker :py:deco:`!pytest.mark.cocotb_runner` that will mark test function as cocotb runner.

.. code:: python

    import pytest
    from cocotb_tools.pytest.hdl import HDL


    @pytest.fixture(name="sample_module")
    def sample_module_fixture(hdl: HDL) -> HDL:
        """Define new HDL design by adding HDL source files to it."""
        hdl.toplevel = "sample_module"
        hdl.sources = (DESIGNS / "sample_module.sv",)
        hdl.build()

        return hdl


    # Request for defined HDL design by using fixture
    @pytest.mark.cocotb_runner  # needed to mark this test function as cocotb runner
    def hdl_runner_1(sample_module: HDL) -> None:
        """Run HDL simulator that will execute cocotb tests."""
        sample_module.test()


    @pytest.mark.cocotb_runner
    @pytest.mark.cocotb_timescale(unit="1ns", precision="1ps")
    def test_dut_using_different_timescale(sample_module: HDL) -> None:
        """Test DUT using different timescale."""
        sample_module.test()


If no positional arguments were provided to :py:deco:`!pytest.mark.cocotb_runner`,
plugin will load current Python module where :py:deco:`!pytest.mark.cocotb_runner` was used as cocotb testbench
(Python file with cocotb tests).

.. code:: python

    @pytest.mark.cocotb_runner
    def test_dut_using_default_testbench(sample_module: HDL) -> None:
        """Test DUT with cocotb tests defined in the same Python file as this test function."""
        sample_module.test()


    async def test_dut_feature_1(dut) -> None:
        """Test DUT feature 1."""
        ...


    async def test_dut_feature_2(dut) -> None:
        """Test DUT feature 2."""
        ...


Additionally, positional arguments of :py:deco:`!pytest.mark.cocotb_runner` marker are equivalent to
``test_module`` argument from :py:meth:`.Runner.test`.

.. code:: python

    @pytest.mark.cocotb_runner("test_dut_tb_1")
    def test_dut_using_different_testbench(sample_module: HDL) -> None:
        """Load ``test_dut_tb_1`` Python module and run cocotb tests from there to test DUT."""
        sample_module.test()


    @pytest.mark.cocotb_runner("test_dut_tb_2", "test_dut_tb_3")
    def test_dut_using_different_testbenches(sample_module: HDL) -> None:
        """Load ``test_dut_tb_2`` and ``test_dut_tb_3`` Python modules and run cocotb tests from there to test DUT."""
        sample_module.test()


If ``toplevel`` argument is empty/non-set, plugin will use name of first test module but without
``test_*`` prefix or ``*_test`` suffix. For example, if test module was ``test_design`` then
name of HDL top level design will be ``design``.

.. code:: python

    # test_design.py

    @pytest.mark.cocotb_runner
    def test_dut_using_default_toplevel(sample_module: HDL) -> None:
        """Test DUT with default top level associated with name of test file as this test function."""
        assert hdl.toplevel == "design"
        sample_module.test()


Using the :deco:`!pytest.mark.cocotb_runner` marker is optional for test functions if they meet the following criteria:

* start with ``test_``
* is a normal function (``def`` without the ``async`` keyword)
* has a positional argument annotated with the :class:`~cocotb_tools.pytest.hdl.HDL` class type

.. code:: python

    # test_*.py

    from cocotb_tools.pytest.hdl import HDL


    def test_sample_module(sample_module: HDL) -> None:
        """Test DUT without explicitly marking this test function with the :deco:`!pytest.mark.cocotb_runner`."""
        sample_module.test()


    async def test_dut_feature_1(dut) -> None:
        """Test DUT feature 1."""
        ...


:py:deco:`!pytest.mark.cocotb_test`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plugin provides the marker :py:deco:`!pytest.mark.cocotb_test` which allows
to mark any coroutine test function as cocotb test.

.. code:: python

    @pytest.mark.cocotb_test
    async def my_test_function(dut) -> None:
        """Function to test DUT feature."""
        ...


Using the :py:deco:`!pytest.mark.cocotb_test` marker is optional for test functions if they meet the following criteria:

* start with ``test_``
* is a coroutine function (``async def``)
* has a positional argument ``dut`` to use the :fixture:`~cocotb_tools.pytest.plugin.dut` fixture

.. code:: python

    async def test_dut_feature(dut) -> None:
        """Function to test DUT feature."""
        ...


Non-``async`` functions marked with :py:deco:`!pytest.mark.cocotb_test` are control functions run by pytest.
They can run simulations by invoking :py:func:`cocotb_tools.pytest.hdl.HDL.test`
or :py:func:`cocotb_tools.runner.Runner.test`.

.. code:: python

    import pytest
    from cocotb_tools.pytest.hdl import HDL


    # First, define new HDL design, add HDL source files to it and build it
    @pytest.fixture(name="sample_module")
    def sample_module_fixture(hdl: HDL) -> HDL:
        """Define new HDL design by adding HDL source files to it."""
        hdl.toplevel = "sample_module"
        hdl.sources = (DESIGNS / "sample_module.sv",)
        hdl.build()

        return hdl


    # Request for defined HDL design by using fixture
    @pytest.mark.cocotb_runner  # needed to mark this test function as cocotb runner
    def hdl_runner(sample_module: HDL) -> None:
        """Run HDL simulator that will execute cocotb tests."""
        hdl.test()


    async def test_something(dut) -> None:
        """Function that is picked up by pytest discovery does not need a decorator."""


    @pytest.mark.cocotb_test
    async def name_without_test_prefix(dut) -> None:
        """Function that is not picked up by pytest discovery needs a decorator to count as a test."""


:py:deco:`!pytest.mark.cocotb_timeout`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The plugin provides the marker :py:deco:`!pytest.mark.cocotb_timeout` which allows to mark coroutine function
with simulation time duration before the test is forced to fail.

.. code:: python

    @pytest.mark.cocotb_timeout(duration=200, unit="ns")
    async def test_dut_feature(dut) -> None:
        """Test DUT feature that must finish before 200 nanoseconds."""
        ...


.. _pytest-plugin-test-discovery:

Test Discovery
==============

Markers can also help the plugin identify and bind cocotb tests to cocotb runners.
This is done based on positional arguments supplied to the :py:deco:`!pytest.mark.cocotb_runner` decorator.
Users can filter tests when invoking `pytest`_  with ``-k '<expression>'`` or ``-m '<markers>'`` options.

List tree hierarchy of cocotb tests related to cocotb runners and cocotb testbenches:

.. code:: shell

   pytest --collect-only

Example output::

    <Dir tests>
      <Module test_sample_module.py>
        <Function test_sample_module>
        <Runner test_sample_module>
          <Testbench test_sample_module>
            <Function test_dut_feature_1>
            <Function test_dut_feature_2>

.. note::

   Functions which build HDL designs and run tests using the cocotb Runner are treated by the plugin as test functions.
   Unfortunately, pytest ``<Function>`` items cannot have other sub-items like cocotb test functions or cocotb test modules.
   So the plugin uses the ``<Runner>`` node to visualize relationship between the cocotb Runner (``<Function>``),
   cocotb test modules (``<Testbench>``) and cocotb tests (``<Function>``).

Run specific test(s) based on output from ``pytest --collect-only``:

.. code:: shell

   pytest -k 'test_sample_module and test_dut_feature_2'

User Fixtures
=============

``pytest`` fixtures can provide useful test functionality, and can use the fixtures provided by the cocotb plugin.

Some examples include:

* Automatically generate a clock.
* Automatically set up (reset, configure) and tear down DUT per each test

Example clock generation for all tests using the ``conftest.py`` file:

.. code:: python

    from collections.abc import AsyncGenerator

    import pytest
    from cocotb.clock import Clock


    @pytest.fixture(scope="session", autouse=True)
    async def clock_generation(dut) -> AsyncGenerator[None, None]:
        """Generate clock for all tests using session scope."""
        # Test setup (executed before test), create and start clock generation
        dut.clk.value = 0

        Clock(dut.clk, 10, unit="ns").start(start_high=False)

        yield  # Calling test, yield is needed to keep clock generation alive

        # Test teardown (executed after test), clock generation will be finished here


Example set up and tear down fixture:

.. code:: python

    from collections.abc import AsyncGenerator

    import pytest
    from cocotb.triggers import FallingEdge


    @pytest.fixture(autouse=True)
    async def setup_sample_module(dut) -> AsyncGenerator[None, None]:
        """Set up and tear down sample module."""
        # Test setup (executed before test)
        dut.rst.value = 1
        dut.stream_in_valid.value = 0
        dut.stream_in_data.value = 0
        dut.stream_out_ready.value = 0

        for _ in range(2):
            await FallingEdge(dut.clk)

        dut.rst.value = 0

        yield  # Calling test

        # Test teardown (executed after test)
        dut.stream_in_valid.value = 0
        dut.stream_in_data.value = 0
        dut.stream_out_ready.value = 0

        await FallingEdge(dut.clk)


    async def test_dut_feature_1(dut) -> None:
        """Test DUT feature 1. DUT will be always correctly reset and configured."""


    async def test_dut_feature_2(dut) -> None:
        """Test DUT feature 2. DUT will be always correctly reset and configured."""


.. _pytest-plugin-integration:

Integration
===========

First, you should follow the chapter about :ref:`custom-flows` to learn how to integrate cocotb into your existing build flow.


Direct Usage
------------

The most straightforward usage with the plugin is to directly invoke build system from a test function.
Example with a custom ``Makefile`` that is defining the ``sample_module`` make recipe:

.. code:: python

    import pytest
    import subprocess

    @pytest.mark.cocotb_runner
    def test_sample_module() -> None:
        """Build and run HDL design."""
        subprocess.run(["make", "sample_module"], check=True)


You may also consider to use command line arguments from pytest to configure build system:

.. code:: python

    import pytest
    import subprocess

    @pytest.mark.cocotb_runner
    def test_sample_module(request: pytest.FixtureRequest) -> None:
        args: list[str] = ["make", "sample_module"]

        # Add additional arguments based on request.config.option.cocotb_* options or
        # from fixtures request.node.iter_markers() like "cocotb" marker
        if request.config.option.cocotb_verbose:
            args.append("VERBOSE=1")

        subprocess.run(args, check=True)


As Fixture
----------

And make it reusable for other projects/teams by packaging is as a new plugin for pytest:

.. code:: python

    import pytest
    import subprocess

    class MyBuildSystem:
        def __init__(self, request: pytest.FixtureRequest) -> None:
            # Handle request.config.option.cocotb_* options and fixtures request.node.iter_markers() like "cocotb" marker
            self.args: list[str] = ["make"]

        def build_and_run(self) -> None:
            # Compile HDL design and run simulator
            subprocess.run(args, check=True)


    @pytest.fixture
    def my_build_system(request: pytest.FixtureRequest) -> MyBuildSystem:
        return MyBuildSystem(request)


So others can use it in their projects:

.. code:: python

    import pytest
    from pytest_cocotb_my_build_system import MyBuildSystem

    @pytest.mark.cocotb_runner
    def test_sample_module(my_build_system: MyBuildSystem) -> None:
        my_build_system.build_and_run()


By Hooks
--------

The most recommended way to integrate custom build flow with :py:mod:`~cocotb_tools.pytest.plugin`
is to implement cocotb pytest hooks defined in :py:mod:`cocotb_tools.pytest.hookspecs`.


.. code:: python

    from pathlib import Path
    from cocotb_tools.pytest.hdl import HDL
    from cocotb_tools.runner import Runner
    from pytest import FixtureRequest, hookimpl


    class MyHDL(HDL):
        def __init__(self, request: FixtureRequest) -> None:
            # Add new attributes, load HDL source files from build system, ...
            ...


    class MyRunner(Runner):
        def build(self, *args, **kwargs) -> None:
            # Build HDL design by invoking existing build system
            ...

        def test(self, *args, **kwargs) -> Path:
            # Run HDL simulator by invoking existing build system
            ...


    @hookimpl(tryfirst=True)
    def pytest_cocotb_make_hdl(request: FixtureRequest) -> HDL:
        return MyHDL(request)


    @hookimpl(tryfirst=True)
    def pytest_cocotb_make_runner(simulator_name: str) -> Runner:
        return MyRunner()


Implemented hooks can be distributed as new Python package published to PyPI registry.

Consider to name published Python package with the ``pytest-cocotb-`` prefix.
This will allow to automatically list your integration in the list of available pytest `plugins`_.


Configuration
=============

Thanks to :py:mod:`cocotb_tools.pytest.plugin`, cocotb can be configured in many ways.

Precedence order of configuring cocotb from the highest to the lowest priority:

1. :py:func:`cocotb_tools.pytest.hdl.HDL` attributes set at fixture or test function level
2. :py:deco:`!pytest.mark.cocotb_runner` marker used with test functions.
3. ``--cocotb-*`` command line arguments when invoking them with `pytest`_ command line interface.
4. ``COCOTB_*`` environment variables.
5. ``cocotb_*`` entries defined in various configuration files like `pyproject.toml`_ file.
6. Default values.

All available command line arguments, configuration entries and environment variables that can be
used to configure cocotb testing environment, can be listed by invoking `pytest`_ help:

.. code:: shell

    pytest --help


.. _pytest-plugin-under-the-hood:

Under the Hood
==============

.. image:: diagrams/svg/pytest_plugin_overview.svg


The :py:mod:`cocotb_tools.pytest.plugin` is split into two independent parts that complement each other.

The first part is performed when invoking the ``pytest`` from command line.
This is the main process that is running in non-simulation environment. It will:

* Identify and mark test function as cocotb runner or cocotb test.
* Collect all tests, including cocotb runners and cocotb tests, when invoking ``pytest`` **with** the ``--collect-only`` option.
  This will allow to properly visualize relationship between cocotb runner, test module (testbench) and cocotb test in
  the ``pytest`` summary report about collected tests (items).
* Collect all non-cocotb tests, including cocotb runners, when invoking ``pytest`` **without** the ``--collect-only`` option.
  This will allow to execute cocotb runners as test functions that will build HDL design and run simulation with cocotb tests.
* Collect serialized test reports sent by cocotb tests via IPC (Inter-Process Communication) from running simulation process.

.. note::

   Cocotb runners are treated by the plugin as test functions and they will be reported in pytest collect and test summary info.
   This will allow to report compilation/elaboration of HDL design and simulation runtimes.

The second part of the :py:mod:`cocotb_tools.pytest.plugin` is performed within the simulator process. It will:

* Identify and mark test function as cocotb test.
* Collect **only** cocotb tests.
* Handle coroutines (asynchronous functions) for requested fixtures, test setup, test call and test teardown.
* Serialize test reports and send them via IPC to the main process (non-simulation environment).


.. _pytest-plugin-options:

Options
=======

.. argparse::
   :module: cocotb_tools.pytest.plugin
   :func: _options_for_documentation
   :prog: pytest

.. _pytest: https://docs.pytest.org/en/stable/contents.html
.. _fixture: https://docs.pytest.org/en/stable/explanation/fixtures.html#about-fixtures
.. _fixtures: https://docs.pytest.org/en/stable/explanation/fixtures.html#about-fixtures
.. _plugins: https://docs.pytest.org/en/stable/reference/plugin_list.html#plugin-list
.. _configuration: https://docs.pytest.org/en/stable/reference/customize.html
.. _pyproject.toml: https://packaging.python.org/en/latest/specifications/pyproject-toml/
.. _marks: https://docs.pytest.org/en/stable/how-to/mark.html
.. _request: https://docs.pytest.org/en/stable/reference/reference.html#request
.. _pytest-xdist: https://github.com/pytest-dev/pytest-xdist
