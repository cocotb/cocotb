.. _howto-runner:

******************************
Building HDL and Running Tests
******************************

.. versionadded:: 1.7

.. warning::
    Python runners and associated APIs are an experimental feature and subject to change.


The Python Test Runner described here is a replacement
for cocotb's traditional Makefile flow.
It builds the HDL for the simulator and runs the tests.

.. note::
    The simulator selection is currently done in the
    :file:`test_{*}.py` files by reading the environment variable ``SIM``.

The runner can be used with `pytest <https://pytest.org>`_
which is Python's go-to testing tool.

For an example on how to set up the runner, see the file
:file:`{cocotb-root}/examples/simple_dff/test_dff.py`,
with the relevant part shown here:

.. literalinclude:: ../../examples/simple_dff/test_dff.py
   :language: python3
   :start-at: def test_simple_dff_runner():
   :end-at: runner.test(toplevel="dff", py_module="test_dff")

You run this file with pytest like

.. code-block:: bash

    SIM=questa TOPLEVEL_LANG=vhdl pytest examples/simple_dff/test_dff.py

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


The API of the Python runner is documented in section :ref:`api-runner`.

The runner reads the following environment variables:

.. envvar:: COCOTB_WAVES

    Record signal traces for later analysis with a waveform viewer.

.. envvar:: COCOTB_GUI

    Run with simulator GUI.
