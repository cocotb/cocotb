**************
Pytest Support
**************

:py:mod:`cocotb_tools.pytest.plugin` provides full `pytest`_ integration with cocotb. Including:

* `fixture`_ to cleanly setup and teardown cocotb tests and designs under test.
* `plugins`_ that can extend cocotb testing capabilities.
* `configuration`_ facilities to configure cocotb testing environment using command line arguments
  ``--cocotb-*``, configuration files like `pyproject.toml`_ or `fixture`_ arguments for fine
  control per test, class, module or session.
* listing all available cocotb tests and their relationship with :py:mod:`cocotb_tools.runner`.
* `marks`_ to easily set metadata on cocotb test functions.
* filtering cocotb tests with `pytest`_ ``-k '<expression>'`` and ``-m '<markers>'`` options.
* reporting all executed cocotb tests.

Enabling Plugin
===============

:py:mod:`cocotb_tools.pytest.plugin` can be enabled in various ways.

When using `pyproject.toml`_ file (recommended way):

.. code:: toml

   [project.entry-points.pytest11]
   cocotb = "cocotb_tools.pytest.plugin"

When using ``pytest.ini`` file:

.. code:: ini

   [pytest]
   addopts = -p cocotb_tools.pytest.plugin

When using ``setup.cfg`` file:

.. code:: ini

   [options.entry_points]
   pytest11 =
     cocotb = cocotb_tools.pytest.plugin

When using ``setup.py`` file:

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

By defining the global variable ``pytest_plugins`` when using ``conftest.py`` file
(it must be located in the root of the project):

.. code:: python

   pytest_plugins = ("cocotb_tools.pytest.plugin",)

By defining the ``PYTEST_PLUGINS`` environment variable:

.. code:: shell

   export PYTEST_PLUGINS="cocotb_tools.pytest.plugin"

By using ``-p <plugin>`` option when invoking `pytest`_ command line interface:

.. code:: shell

   pytest -p cocotb_tools.pytest.plugin ...

Building and Testing
====================

:py:class:`cocotb_tools.pytest.hdl.HDL` wraps :py:class:`cocotb_tools.runner.Runner`
and allows to fully configure it by using command line arguments ``--cocotb-*``,
configuration files like `pyproject.toml`_ or `fixture`_ arguments. This is possible
by binding `pytest`_ built-in `request`_ fixture that is providing information of the requesting
test function including current configuration of `pytest`_.

In most cases, we want to build HDL design only once before we will start invoking tests.
This can be achieved by using scoped `fixture`_ that will be set to ``session``.
We can create ``conftest.py`` file that will contain defined `fixture`_ and make them
available for all tests defined in ``test_*.py`` files in the same directory.

Example content of ``conftest.py`` file:

.. code:: python

   import pytest
   from cocotb_tools.pytest.hdl import HDL


   @pytest.fixture(name="hdl_build", scope="session")
   def hdl_build_fixture(request: pytest.FixtureRequest) -> HDL:
       """Build HDL design only once before invoking all tests.

       Args:
           request: Used to bind fixture request with session scope to
                    new HDL design instance. Needed to support configuration
                    including command line arguments ``--cocotb-*``,
                    configuration files or fixture arguments but limited to session scope only.

       Returns:
           New instance of HDL design with HDL runner to build design and run tests.
       """
       hdl: HDL = HDL(request)  # bind provided fixture request with session scope

       # It will invoke cocotb_tools.runner.Runner.build() method
       # but with configuration information from fixture request object
       hdl.build(
           sources=(
               # List HDL source files,
               "dut.sv",
           ),
       )

       return hdl


    @pytest.fixture(name="hdl")
    def hdl_fixture(hdl_build: HDL, request: pytest.FixtureRequest) -> HDL:
        """Bind fixture request object but from function scope.

        Fixture required later to invoke test for HDL top level design.

        Args:
            hdl_build: User defined fixture that built HDL design.
            request:   Fixture request but with function scope (default) that can
                       access to all fixtures and markers from all other scopes.

        Returns:
            New instance of HDL design but with function scope (test).
        """
        return hdl.from_request(request)


Example content of ``test_dut.py`` file:

.. code:: python

   import pytest
   from cocotb_tools.pytest.hdl import HDL


   # Without providing positional arguments or test_module option to cocotb decorator,
   # plugin will use current file as cocotb testbench (Python file with cocotb tests).
   # If hdl_toplevel option was not provided, it will be based on name of first test_module
   # but with removed test_* prefix or *_test suffix.
   @pytest.mark.cocotb  # equivalent to @pytest.mark.cocotb("test_dut", hdl_toplevel="dut")
   def test_dut(hdl: HDL) -> None:
       """Run HDL simulator with built HDL design and start invoking defined cocotb tests.

       Args:
           hdl: Instance of built HDL design ready to run.
       """
       hdl.test()


   # @pytest.mark.cocotb or @cocotb.test decorator is not required if test function
   # starts with test_* prefix, is coroutine function (``async``) and with ``dut`` argument.
   async def test_some_dut_feature(dut) -> None:
        """Cocotb test for DUT."""

@pytest.mark.cocotb
===================

Provided ``@pytest.mark.cocotb`` marker by :py:mod:`cocotb_tools.pytest.plugin` allows
to configure all aspects of cocotb test and cocotb runner. Marker recognizes all
named arguments from :py:func:`cocotb.test` and :py:class:`cocotb_tools.runner.Runner`.
Additionally, positional arguments of ``@pytest.mark.cocotb`` marker are equivalent to
``test_module`` argument from :py:func:`cocotb.test`.

If no positional arguments were provided to ``@pytest.mark.cocotb`` or ``test_module`` argument is empty/non-set,
plugin will load current Python module where ``@pytest.mark.cocotb`` was used as cocotb testbench (Python file with
cocotb tests).

If ``hdl_toplevel`` argument is empty/non-set, plugin will use name of first test module but without
``test_*`` prefix or ``*_test`` suffix. For example, if test module was ``test_dut`` then
name of HDL top level design will be ``dut``.

Using ``@pytest.mark.cocotb`` marker to mark test function as cocotb test is optional
for test functions that are starting with ``test_*`` prefix name, are coroutine functions (``async def``) and
and with ``dut`` argument. Normal functions (non-coroutines) with ``@pytest.mark.cocotb`` marker are
marked as cocotb runner that should run HDL simulator by invoking
:py:func:`cocotb_tools.pytest.hdl.HDL.test`, :py:func:`cocotb_tools.runner.Runner.test` or similar method.

Marker can also help plugin to identify and bind cocotb tests to cocotb runners. This is done by plugin
based on information from provided positional arguments (or cocotb ``test_module`` argument) supplied into
``@pytest.mark.cocotb`` decorator. This helps plugin to properly filter tests out
when using `pytest`_ ``-k '<expression>'`` or ``-m '<markers>'`` options.

.. code:: python

   import pytest
   from cocotb_tools.pytest.hdl import HDL


   @pytest.mark.cocotb  # needed by cocotb runners
   def hdl_runner(hdl: HDL) -> None:
       """Run HDL simulator with built HDL design and start invoking defined cocotb tests."""


   async def test_something(dut) -> None:
       """Test DUT with standard name for test function defined by pytest."""


   @pytest.mark.cocotb  # needed by cocotb tests using non-standard names
   async def name_without_test_prefix(dut) -> None:
       """Test DUT with non-standard name for test function."""

Configuration
=============

Thanks to :py:mod:`cocotb_tools.pytest.plugin`, cocotb can be configured in many ways.

Precedence order of configuring cocotb from the highest to the lowest priority:

1. Using named arguments when invoking :py:func:`cocotb_tools.pytest.hdl.HDL.build` or
   :py:func:`cocotb_tools.pytest.hdl.HDL.test` methods.
2. ``@pytest.mark.cocotb`` marker used with test functions.
3. ``--cocotb-*`` command line arguments when invoking them with `pytest`_ command line interface.
4. ``COCOTB_*`` environment variables.
5. ``cocotb_*`` entries defined in various configuration files like `pyproject.toml`_ file.
6. Default values.

All available command line arguments, configuration entries and environment variables that can be
used to configure cocotb testing environment, can be listed by invoking `pytest`_ help:

.. code:: shell

   pytest --help

Command Line Usage
==================

.. note::

   :py:mod:`cocotb_tools.pytest.plugin` must be enabled for `pytest`_ to show all
   available command line arguments `--cocotb-*`, markers and fixtures for cocotb.

Help
----

Show all available command line arguments:

.. code:: shell

   pytest --help

Show all available markers:

.. code:: shell

   pytest --markers

Show all available fixtures:

.. code:: shell

   pytest --fixtures

Tests Discovering
-----------------

To list all available tests, use the ``--co`` or alternatively the ``--collect-only`` option:

.. code:: shell

   pytest --co

To show also docstring when listing tests, add the ``-v`` option:

.. code:: shell

   pytest --co -v

To list only cocotb tests and cocotb runners, use the ``-k cocotb`` option:

.. code:: shell

   pytest --co -k cocotb

To list only cocotb tests without cocotb runners, use the ``-k 'cocotb and not runner'`` option:

.. code:: shell

   pytest --co -k 'cocotb and not runner'


To list only cocotb runners without cocotb tests, use the ``-k 'cocotb and runner'`` option:

.. code:: shell

   pytest --co -k 'cocotb and runner'

To list only cocotb tests that will be run by specific cocotb runner, add name of cocotb runner test function:

.. code:: shell

   pytest --co -k 'cocotb and not runner and <name-of-cocotb-runner-test-function>'

To list which cocotb runners will run specific cocotb test(s), add name of cocotb test function:

.. code:: shell

   pytest --co -k 'cocotb and runner and <name-of-cocotb-test-function>'

Running Tests
-------------

To run all tests (including cocotb and non-cocotb tests):

.. code:: shell

   pytest

To run only cocotb tests:

.. code:: shell

   pytest -k cocotb

To see output from tests in real-time, disable capture mode with the ``-s`` option or the ``--capture=no`` option:

.. code:: shell

   pytest -s

To see more verbose information about test, add the ``-v`` option:

.. code:: shell

   pytest -s -v

Tests Reporting
---------------

To show extra test summary from all tests regardless of passed or failed status:

.. code:: shell

   pytes -rA

To show classic cocotb tests summary report:

.. code:: shell

   pytest --cocotb-summary

To generate JUnit XML tests report file for CI:

.. code:: shell

   pytest --junit-xml=junit.xml -o junit_family=xunit1

.. note::

   Changing JUnit family to ``xunit1`` will tell built-in `pytest`_ JUnit XML plugin to include also
   file path and line number of executed test function (testcase) in generated JUnit XML tests report.
   These information can be used by CI environments like GitLab CI.

pytest-xdist
============

Support for the `pytest-xdist`_ plugin is planned. It will require few things before it can be safely used:

* HDL simulators defined in :py:mod:`cocotb_tools.runner` module must properly handle
  their build directory and test directories in that way where builds and tests are immutable
  and can be safely executed in parallel without any unexpected side affects between them.
  This condition is not met for some HDL simulators support.
* `Making session scoped fixtures execute only once`_ for HDL builds

.. _pytest: https://docs.pytest.org/en/stable/contents.html
.. _fixture: https://docs.pytest.org/en/stable/explanation/fixtures.html#about-fixtures
.. _plugins: https://docs.pytest.org/en/stable/reference/plugin_list.html#plugin-list
.. _configuration: https://docs.pytest.org/en/stable/reference/customize.html
.. _pyproject.toml: https://packaging.python.org/en/latest/specifications/pyproject-toml/
.. _marks: https://docs.pytest.org/en/stable/how-to/mark.html
.. _request: https://docs.pytest.org/en/stable/reference/reference.html#request
.. _pytest-xdist: https://github.com/pytest-dev/pytest-xdist
.. _Making session scoped fixtures execute only once:
   https://pytest-xdist.readthedocs.io/en/stable/how-to.html#making-session-scoped-fixtures-execute-only-once
