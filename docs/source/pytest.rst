**************
Pytest Support
**************

:py:mod:`cocotb_tools.pytest.plugin` provides full `pytest`_ integration with cocotb. Including:

* `fixtures`_ to cleanly set up and tear down cocotb tests and designs under test.
* `plugins`_ that can extend cocotb testing capabilities.
* `configuration`_ facilities to configure the cocotb testing environment using command line arguments
  ``--cocotb-*``, configuration files like `pyproject.toml`_ or `fixture`_ arguments for fine
  control per test, class, module or session.
* listing all available cocotb tests and their relationship with :py:mod:`cocotb_tools.runner`.
* `marks`_ to easily set metadata on cocotb test functions.
* filtering cocotb tests with `pytest`_ ``-k '<expression>'`` and ``-m '<markers>'`` options.
* reporting all executed cocotb tests.
* parallel execution of cocotb runners by using the `pytest-xdist`_ plugin

Enabling the Plugin
===================

:py:mod:`cocotb_tools.pytest.plugin` can be enabled in various ways.

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

Building and Testing
====================

:py:class:`cocotb_tools.pytest.hdl.HDL` wraps :py:class:`cocotb_tools.runner.Runner`
allowing to fully configure the cocotb runner by using the command line arguments ``--cocotb-*``,
configuration files like `pyproject.toml`_ or `fixture`_ arguments.

The plugin provides a ``hdl`` fixture that will create a new instance of :py:class:`cocotb_tools.pytest.hdl.HDL`
with the `pytest`_ built-in `request`_ fixture that is providing information of the requesting test function
including the current configuration of `pytest`_.

Example content of a ``conftest.py`` file:

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

        return hdl


Example content of the ``test_sample_module.py`` file:

.. code:: python

    import pytest
    from cocotb_tools.pytest.hdl import HDL


    # Without providing positional arguments to the cocotb decorator,
    # the plugin will use the current file as the cocotb testbench (a Python file with cocotb tests).
    # If the 'toplevel' option was not provided, it will be derived from the name of the first positional argument
    # but with a removed 'test_*' prefix or '*_test' suffix.
    @pytest.mark.cocotb  # equivalent to @pytest.mark.cocotb("test_dut", toplevel="dut")
    def test_sample_module(sample_module: HDL) -> None:
        """Build HDL design and run HDL simulator to execute cocotb tests.

        Args:
            sample_module: An instance of a defined HDL design.
        """
        sample_module.test()


    # A @pytest.mark.cocotb or @cocotb.test decorator is not required if the test function
    # starts with a 'test_*' prefix, is a coroutine function (``async``) and has a ``dut`` argument.
    async def test_some_dut_feature(dut) -> None:
        """cocotb test for DUT."""

@pytest.mark.cocotb
===================

The plugin provides the marker ``@pytest.mark.cocotb`` which allows
to configure all aspects of cocotb test and cocotb runner.

.. code:: python

    @pytest.mark.cocotb(timescale=("1ns", "1ps"))
    def test_dut_using_different_timescale(sample_module: HDL) -> None:
        """Test DUT using different timescale."""
        sample_module.test()

    @pytest.mark.cocotb(timeout=(200, "ns"))
    async def test_dut_feature_with_timeout(dut) -> None:
        """Test DUT feature. It must finish within 200 nanoseconds."""

Additionally, positional arguments of ``@pytest.mark.cocotb`` marker are equivalent to
``test_module`` argument from :py:func:`cocotb.test`.

.. code:: python

    @pytest.mark.cocotb("test_dut_tb_1", "test_dut_tb_2")
    def test_dut_using_different_testbenches(sample_module: HDL) -> None:
        """Use cocotb tests from ``test_dut_tb_1.py`` and ``test_dut_tb_2.py`` files to test DUT."""
        sample_module.test()

If no positional arguments were provided to ``@pytest.mark.cocotb``,
plugin will load current Python module where ``@pytest.mark.cocotb`` was used as cocotb testbench (Python file with
cocotb tests).

.. code:: python

    @pytest.mark.cocotb
    def test_dut_using_default_testbench(sample_module: HDL) -> None:
        """Test DUT with cocotb tests defined in the same Python file as this test function."""
        sample_module.test()

    async def test_dut_feature_1(dut) -> None:
        """Test DUT feature 1."""

If ``toplevel`` argument is empty/non-set, plugin will use name of first test module but without
``test_*`` prefix or ``*_test`` suffix. For example, if test module was ``test_dut`` then
name of HDL top level design will be ``dut``.

.. code:: python

    @pytest.mark.cocotb
    def test_dut_using_default_toplevel(sample_module: HDL) -> None:
        """Test DUT with default top level associated with name of test file as this test function."""
        sample_module.test()

    @pytest.mark.cocotb(toplevel="sample_submodule")
    def test_dut_using_different_toplevel(sample_module: HDL) -> None:
        """Test DUT with different top level that was set at fixture level."""
        sample_module.test()

Using ``@pytest.mark.cocotb`` marker to mark test function as cocotb test is optional
for test functions that are starting with ``test_*`` prefix name, are coroutine functions (``async def``) and
with ``dut`` argument. Normal functions (non-coroutines) with ``@pytest.mark.cocotb`` marker are
marked as cocotb runner that should run HDL simulator by invoking
:py:func:`cocotb_tools.pytest.hdl.HDL.test`, :py:func:`cocotb_tools.runner.Runner.test` or similar method.

.. code:: python

    import pytest
    from cocotb_tools.pytest.hdl import HDL


    @pytest.mark.cocotb  # needed by cocotb runners
    def hdl_runner(hdl: HDL) -> None:
        """Build HDL design and run HDL simulator that will execute cocotb tests."""
        hdl.test()


    async def test_something(dut) -> None:
        """Function that is picked up by pytest discovery does not need a decorator."""


    @pytest.mark.cocotb
    async def name_without_test_prefix(dut) -> None:
        """Function that is not picked up by pytest discovery needs a decorator to count as a test."""

Marker can also help plugin to identify and bind cocotb tests to cocotb runners. This is done by plugin
based on information from provided positional arguments supplied into
``@pytest.mark.cocotb`` decorator. This helps plugin to properly filter tests out
when using `pytest`_ ``-k '<expression>'`` or ``-m '<markers>'`` options.

List tree hierarchy of cocotb tests related to cocotb runners and cocotb testbenches:

.. code:: shell

   pytest --collect-only

Example output::

    <Dir tests>
      <Module test_sample_module.py>
        <Runner test_sample_module>
          <Testbench test_sample_module>
            <Function test_dut_feature_1>
            <Function test_dut_feature_2>

Run specific test(s) based on output from ``pytest --collect-only``:

.. code:: shell

   pytest -k 'test_sample_module and test_dut_feature_2'

Fixtures
========

Usage:

* Automatically generate clock for all tests
* Automatically set up (reset, configure) and tear down DUT per each test

Example of automatically generating clock for all tests using the ``conftest.py`` file:

.. code:: python

    import pytest
    from cocotb.clock import Clock


    @pytest.fixture(scope="session", autouse=True)
    async def clock_generation(dut) -> None:
        """Generate clock for all tests using session scope."""
        dut.clk.value = 0

        Clock(dut.clk, 10, unit="ns").start(start_high=False)


Example of automatically set up (reset, configure) and tear down DUT per each test defined in ``test_*.py`` file:

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


Configuration
=============

Thanks to :py:mod:`cocotb_tools.pytest.plugin`, cocotb can be configured in many ways.

Precedence order of configuring cocotb from the highest to the lowest priority:

1. :py:func:`cocotb_tools.pytest.hdl.HDL` attributes set at fixture or test function level
2. ``@pytest.mark.cocotb`` marker used with test functions.
3. ``--cocotb-*`` command line arguments when invoking them with `pytest`_ command line interface.
4. ``COCOTB_*`` environment variables.
5. ``cocotb_*`` entries defined in various configuration files like `pyproject.toml`_ file.
6. Default values.

All available command line arguments, configuration entries and environment variables that can be
used to configure cocotb testing environment, can be listed by invoking `pytest`_ help:

.. code:: shell

    pytest --help

Options
=======

.. argparse::
   :module: cocotb_tools.pytest.plugin
   :func: options_for_documentation

.. _pytest: https://docs.pytest.org/en/stable/contents.html
.. _fixture: https://docs.pytest.org/en/stable/explanation/fixtures.html#about-fixtures
.. _fixtures: https://docs.pytest.org/en/stable/explanation/fixtures.html#about-fixtures
.. _plugins: https://docs.pytest.org/en/stable/reference/plugin_list.html#plugin-list
.. _configuration: https://docs.pytest.org/en/stable/reference/customize.html
.. _pyproject.toml: https://packaging.python.org/en/latest/specifications/pyproject-toml/
.. _marks: https://docs.pytest.org/en/stable/how-to/mark.html
.. _request: https://docs.pytest.org/en/stable/reference/reference.html#request
.. _pytest-xdist: https://github.com/pytest-dev/pytest-xdist
