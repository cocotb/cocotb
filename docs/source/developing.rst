*****************
Developing cocotb
*****************

Setting Up a Development Environment
====================================

:ref:`Install prerequisites to build the development version of cocotb <install-devel>` and standard development tools (editor, shell, git, etc.).

.. note:: Documentation generation requires Python 3.11+.

First, you should `fork and clone <https://guides.github.com/activities/forking/>`__ the cocotb repo to your machine.
This will allow you to make changes to the cocotb source code, create pull requests, and run regressions and build documentation locally.

You will need `doxygen <https://www.doxygen.nl/index.html>`__, for building documentation.
We recommend if you are using a Linux distribution to use your system package manager to install doxygen.
Likewise, doxygen can be installed using the homebrew package manager on Mac OS.
Windows contributors should download a binary distribution installer from the main website.

Next install `uv <https://docs.astral.sh/uv/getting-started/installation/>`__,
which is a tool for managing Python virtual environments and dependencies.

After ``uv`` is installed, run the following command in the project root to build a virtual environment for development.

.. code:: bash

   uv venv

This will create a virtual environment and print instructions on how to activate it.
After you activate the virtual environment, you can install the development dependencies with the following command:

.. code:: bash

   uv sync --dev

.. note::
   We recommend using `direnv <https://direnv.net/>`__ to automatically activate the virtual environment when you navigate into the project directory.

To enable pre-commit, run the following command at the root of the cloned project to install the git hooks.
The first run of pre-commit will build an environment for you, so it may take a while.
Following runs should be much quicker.

.. code:: bash

   pre-commit install

When committing, pre-commit's hook will run, checking your changes for formatting, code smells, etc.
You will see the lists of checks printed and whether they passed, were skipped, or failed.
If any of the checks fail, it is recommended to fix them before opening a pull request,
otherwise the pull request checks will fail as well.

Now you are ready to contribute!

Running Tests Locally
=====================

First, `set up your development environment <#setting-up-a-development-environment>`__.

Our tests are managed by ``nox``, which runs both ``pytest`` tests and our system of makefiles.
The regression does not end on the first failure, but continues until all tests in the ``/tests`` and ``/examples`` directories have been run.

To run the tests locally with ``nox``, issue the following command.

.. code:: bash

   nox -s dev_test

At the end of the regression, if there were any test failures, the tests that failed will be printed.
If the tests succeed you will see the message ``Session tests was successful`` printed in green.

By default the ``dev_test`` nox session runs all simulator-agnostic tests, as well as all tests which require a simulator and can be run against Icarus Verilog.
Icarus Verilog must be installed.

The simulator and the toplevel language can be changed by setting the environment variables :make:var:`SIM` and :make:var:`TOPLEVEL_LANG`.
Alternatively, the simulator-specific nox sessions can be used, as described below.

Selecting a Language and Simulator for Regression
=================================================

cocotb can be used with multiple simulators, and can run tests against all of them.
Nox provides a session for each valid simulator/language/GPI interface combination, from which one or multiple sessions can be selected.

The following examples are good starting points;
refer to the `nox command-line usage documentation <https://nox.thea.codes/en/stable/usage.html>`__ for more information.

.. code:: bash

   # List all available sessions.
   nox -l

   # Run all simulator-agnostic tests.
   nox -s dev_test_nosim

   # Run the simulator-specific tests against Xcelium, using a VHDL toplevel and
   # the VHPI interface.
   nox -s "dev_test_sim(sim='xcelium', toplevel_lang='vhdl', gpi_interface='vhpi')"

   # Run all simulator-specific tests against Icarus Verilog and GHDL.
   # Both simulators must be installed locally.
   nox -k "dev_test_sim and (icarus or ghdl)"

Running Individual Tests Locally
================================

Each test under ``/tests/test_cases/*/`` and ``/examples/*/tests/`` can be run individually.
This is particularly useful if you want to run a particular test that fails the regression.

First you must install cocotb from source by navigating to the project root directory and issuing the following command:

.. code:: bash

   python -m pip install .

On Windows, you must instead install cocotb from source like so:

.. code:: bash

   python -m pip install --global-option build_ext --global-option --compiler=mingw32 .

Once that has been done, you can navigate to the directory containing the test you wish to run.
Then you may issue an :ref:`make <building>` command.
For example, if you want to test with Icarus using Verilog sources:

.. code:: bash

   make SIM=icarus TOPLEVEL_LANG=verilog

Building Documentation Locally
==============================

First, `set up your development environment <#setting-up-a-development-environment>`__.

Documentation is built locally using ``nox``.
The last message in the output will contain a URL to the documentation you just built.
Simply copy and paste the link into your browser to view it.
The documentation will be built in the same location on your hard drive on every run, so you only have to refresh the page to see new changes.

To build the documentation locally on Linux or Mac, issue the following command:

.. code:: bash

   nox -e docs

Building the documentation is not currently supported on Windows.
