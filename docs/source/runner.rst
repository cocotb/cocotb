.. _howto-python-runner:

******************************************
Building HDL and Running Tests with Python
******************************************

.. versionadded:: 1.8

.. warning::
    Python runners and associated APIs are an experimental feature and subject to change.


The Python Test Runner (short: "runner") described here is a replacement
for cocotb's traditional Makefile flow.
It builds the :term:`HDL` for the simulator and runs the tests.

It is not meant to be the ideal solution for everyone.
You can easily integrate cocotb into your custom flow, see :ref:`custom-flows`.


.. _runner-with-pytest:

Usage with pytest
=================

The runner can be used with `pytest <https://pytest.org>`_
which is Python's go-to testing tool.

For an example on how to set up the runner with pytest,
see the file
:file:`{cocotb-root}/examples/simple_dff/test_dff.py`,
with the relevant part shown here:

.. autolink-preface:: from cocotb_tools.runner import get_runner
.. literalinclude:: ../../examples/simple_dff/test_dff.py
   :language: python
   :start-at: def test_simple_dff_runner():
   :end-at: runner.test(hdl_toplevel="dff", test_module="test_dff")

You run this file with pytest like

.. code-block:: bash

    SIM=questa TOPLEVEL_LANG=vhdl pytest examples/simple_dff/test_dff.py

Note that the environment variables ``SIM`` and ``TOPLEVEL_LANG``
are defined in this test file to set arguments to the runner's
:meth:`Runner.build <cocotb_tools.runner.Runner.build>` and :meth:`Runner.test <cocotb_tools.runner.Runner.test>` functions;
they are not directly handled by the runner itself.

Test filenames and functions have to follow the
`pytest discovery <https://docs.pytest.org/explanation/goodpractices.html#test-discovery>`_
convention in order to be automatically found.

By default, pytest will only show you a terse "pass/fail" information.
To see more details of the simulation run,
including the output produced by cocotb,
add the ``-s`` option to the ``pytest`` call:

.. code-block:: bash

    SIM=questa TOPLEVEL_LANG=vhdl pytest examples/simple_dff/test_dff.py -s

.. note::
    Take a look at the
    :ref:`list of command line flags <pytest:command-line-flags>`
    in pytest's official documentation.


Direct usage
============

You can also run the test directly, that is, without using pytest, like so

.. code-block:: bash

    python examples/simple_dff/test_dff.py

This requires that you define the test to run in the testcase file itself.
For example, add the following code at the end:

.. code-block:: bash

    if __name__ == "__main__":
        test_simple_dff_runner()

.. _runner-checking-results:

Checking test results
=====================

Whether :meth:`.Runner.test` reports failing cocotb tests
depends on how it is called.

When called from a pytest test, it also checks the results file.
The pytest test fails if any cocotb test failed,
if no results file was written,
or if the simulator exited with a non-zero status.

When used directly, it does not read the results file.
It raises an exception if the simulator exits with a non-zero status,
and otherwise returns the path to the results file,
even if cocotb tests failed or the file was not written.
To make a script fail when cocotb tests fail,
check the returned file, for example with :func:`~cocotb_tools.runner.get_results`,
which also raises an exception if the file does not exist:

.. code-block:: python

    import sys

    from cocotb_tools.runner import get_results

    results_xml = runner.test(hdl_toplevel="dff", test_module="test_dff")
    num_tests, num_failed = get_results(results_xml)
    if num_failed:
        sys.exit(f"{num_failed} of {num_tests} tests failed")

Generate waveforms
==================

For many simulators it is possible to generate simulation waveforms.
This can be done by setting the *waves* argument to ``True`` in the
:meth:`Runner.build <cocotb_tools.runner.Runner.build>` and :meth:`Runner.test <cocotb_tools.runner.Runner.test>` functions.
It is also possible to set the environment variable :envvar:`WAVES` to
a non-zero value to generate waveform files at run-time without modifying the test code, e.g.,

.. code-block:: bash

    WAVES=1 pytest examples/simple_dff/test_dff.py

Similarly, it is possible to disable the waveform generation set in the test
code by setting ``WAVES`` to 0.

Starting in GUI mode/viewing waveforms
======================================

To start the simulator GUI or, for simulators not having a GUI, view
the waveform file in a waveform viewer after the simulation, it is possible
to set the *gui* argument to ``True`` in :meth:`Runner.test <cocotb_tools.runner.Runner.test>`.
It is also possible to set the :envvar:`GUI` environment variable to a non-zero value, e.g.,

.. code-block:: bash

    GUI=1 pytest examples/simple_dff/test_dff.py

For simulators without a GUI, cocotb will open a waveform viewer. Either `Surfer <https://surfer-project.org/>`_
or `GTKWave <https://gtkwave.github.io/gtkwave/>`_, in that order, if available in the system path.
To specify preferred waveform viewer, the :envvar:`COCOTB_WAVEFORM_VIEWER` environment variable
can be used. This can also be used to set, e.g., the ``surfer.sh`` startup script for WSL.

API
===

The API of the Python runner is documented in section :ref:`api-runner`.
