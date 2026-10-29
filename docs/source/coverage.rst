********************
Python Code Coverage
********************

cocotb provides support for collecting Python code coverage via the `coverage <https://coverage.readthedocs.io/>`_ package.

There are two main approaches to enabling coverage collection in cocotb regressions:
using the :envvar:`!COCOTB_USER_COVERAGE` environment variable, which is a temporary enablement,
or by instrumenting your environment with :mod:`!coverage`'s :mod:`!sitecustomize` hook, which is a more permanent solution.

The first step in either approach is to install the :mod:`!coverage` package if you haven't already.

.. code-block:: bash

   pip install coverage


Using :envvar:`!COCOTB_USER_COVERAGE`
=====================================

cocotb provides the :envvar:`COCOTB_USER_COVERAGE` environment variable to enable coverage collection for the current regression.
This solution is ideal for users who only want to collect coverage occasionally or on a per-regression basis,
or don't want to permanently modify their Python environment.

To enable coverage collection, set :envvar:`!COCOTB_USER_COVERAGE` to ``1`` before running your tests.
The :mod:`!coverage` module will use the :envvar:`COVERAGE_RCFILE` environment variable to find the configuration file to determine what to measure.
If :envvar:`!COVERAGE_RCFILE` is not set, cocotb provides a default configuration that collects line and branch coverage for all Python modules
except those in the ``cocotb``, ``cocotb_tools``, and ``pygpi`` package directories.

.. code-block:: bash

   export COCOTB_USER_COVERAGE=1
   # optional, only if you want to use a custom config file
   export COVERAGE_RCFILE=path/to/your/.coveragerc

   pytest
   # or
   make

This will create a file named ``.coverage`` in the directory where the test was run.


Instrumenting your environment with :mod:`!coverage`'s :mod:`!sitecustomize` hook
=================================================================================

This approach works well for users who regularly collect coverage across
subprocesses in their environment and want a single configuration that
applies everywhere.

The :mod:`!coverage` module provides support for automatically collecting coverage for all packages in a Python environment
regardless of how Python is invoked (e.g. via embedding a Python interpreter in a simulator) for a process and all its subprocesses.
This requires installing a :mod:`sitecustomize` hook that starts coverage measurement in any Python process.

Follow the instructions in the `coverage documentation <https://coverage.readthedocs.io/en/latest/subprocess.html#manual-sub-process-coordination>`_ to add this hook.

Then, to collect coverage for your cocotb tests, do the following:

1. Create a ``.coveragerc`` configuration file specifying what to measure:

   .. code-block:: ini

      [run]
      branch = True
      source = my_package

2. Set the ``COVERAGE_PROCESS_START`` environment variable and run your
   tests. The exact command depends on how you run cocotb:

   .. tab-set::

      .. tab-item:: Makefile-based flow

         .. code-block:: bash

            export COVERAGE_PROCESS_START=.coveragerc
            make

      .. tab-item:: Python Runner

         .. code-block:: bash

            export COVERAGE_PROCESS_START=.coveragerc
            python my_test_script.py

      .. tab-item:: pytest

         .. code-block:: bash

            export COVERAGE_PROCESS_START=.coveragerc
            coverage run --parallel-mode -m pytest

This will create a file named ``.coverage`` in the directory where the test was run.


Combining coverage data from multiple runs
==========================================

If you run your tests multiple times with coverage collection enabled from the same directory,
cocotb will automatically load the configured coverage data from previous runs to append all coverage data together.

However, if you are running tests in multiple directories, or running tests in parallel, you may end up with multiple ``.coverage`` files.
You can combine the resulting ``.coverage`` files into a single file using the `combine <https://coverage.readthedocs.io/en/latest/commands/cmd_combine.html#cmd-combine>`_ command.

.. code-block:: bash

   coverage combine path/to/.coverage path/to/other/.coverage

This will create a new ``.coverage`` file that combines the data from the specified files.


Viewing the coverage data
=========================

After running your tests with coverage collection enabled, you can use the `coverage command-line tool <https://coverage.readthedocs.io/en/latest/commands/index.html>`_ to view the results.

The simplest way to view the results is to use the `report <https://coverage.readthedocs.io/en/latest/commands/cmd_report.html#cmd-report>`_ command.
This will print a summary of the coverage including the number of statements that were hit and missed, the missed line numbers, and overall coverage percentage, to the terminal.

.. code-block:: bash

   coverage report

For a more detailed view, you can use the `html <https://coverage.readthedocs.io/en/latest/commands/cmd_html.html#cmd-html>`_ command to generate an HTML report.

.. code-block:: bash

   coverage html

This will create an ``htmlcov`` directory with an ``index.html`` file that you can open in a web browser which will allow you to navigate your testbench and the libraries it uses,
and will show coverage details annotated on the source code.
