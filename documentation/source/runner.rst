.. _howto-python-runner:

******************************
Building HDL and Running Tests
******************************

.. versionadded:: 1.7

.. warning::
    Python runners and associated APIs are an experimental feature and subject to change.


The Python Test Runner (short: "runner") described here is a replacement
for cocotb's traditional Makefile flow.
It builds the HDL for the simulator and runs the tests.


Command-line Interface
======================

The runner has a command-line interface under the name ``cocotb-runner``.

The following is an example on how to run the tests in file
:file:`{cocotb-root}/examples/simple_dff/test_dff.py`
against the design
:file:`{cocotb-root}/examples/simple_dff/dff.sv`.

.. code-block:: bash

    PYTHONPATH=examples/simple_dff cocotb-runner \
        --hdl-toplevel=dff \
        --test-module=test_dff \
        --verilog-sources=examples/simple_dff/dff.sv


See the full list of supported runner arguments by running ``cocotb-runner -h``.

``cocotb-runner`` will set the return code ``1``
if no tests have been run at all
or if any failures have been found in the result files.
It will return ``0`` otherwise.


Usage with pytest
=================

The runner can be used with `pytest <https://pytest.org>`_
which is Python's go-to testing tool.

For an example on how to set up the runner with pytest,
see the file
:file:`{cocotb-root}/examples/simple_dff/test_dff.py`,
with the relevant part shown here:

.. literalinclude:: ../../examples/simple_dff/test_dff.py
   :language: python3
   :start-at: def test_simple_dff_runner():
   :end-at: runner.test(hdl_toplevel="dff", test_module="test_dff")

You run this file with pytest like

.. code-block:: bash

    SIM=questa HDL_TOPLEVEL_LANG=vhdl pytest examples/simple_dff/test_dff.py

Note that the environment variables ``SIM`` and ``HDL_TOPLEVEL_LANG``
are defined in this test file to set arguments to the runner's
:meth:`~cocotb.runner.build` and :meth:`~cocotb.runner.test`  functions;
they are not directly handled by the runner itself.

FIXME: mention testcase naming scheme ``foo_test``

By default, pytest will only show you a terse "pass/fail" information.
To see more details of the simulation run,
including the output produced by cocotb,
add the ``-s`` option to the ``pytest`` call:

.. code-block:: bash

    SIM=questa HDL_TOPLEVEL_LANG=vhdl pytest examples/simple_dff/test_dff.py -s

.. note::
    Take a look at the
    :ref:`list of command line flags <pytest:command-line-flags>`
    in pytest's official documentation.

Direct usage
=============

You can also run the test directly.

.. code-block:: bash

    python examples/simple_dff/test_dff.py

For this you need to define the test to run in the script. For example:

.. code-block:: bash

    if __name__ == "__main__":
        test_simple_dff_runner()

API
===

The API of the Python runner is documented in section :ref:`api-runner`.
