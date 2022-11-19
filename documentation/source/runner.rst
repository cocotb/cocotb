.. _howto-python-runner:

******************************
Building HDL and Running Tests
******************************

.. versionadded:: 1.8

.. warning::
    Python runners and associated APIs are an experimental feature and subject to change.


The Python Test Runner (short: "runner") described here is a replacement
for cocotb's traditional Makefile flow.
It builds the HDL for the simulator and runs the tests.

It is not meant to be ideal solution for everyone.
You can easily integrate cocotb into your custom flow, see :ref:`custom-flows`.


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
:meth:`~cocotb.runner.build` and :meth:`~cocotb.runner.test` functions;
they are not directly handled by the runner itself.

Test filenames and functions have to follow the
`pytest discovery <https://docs.pytest.org/explanation/goodpractices.html#test-discovery>`_
convention in order to be automatically found.

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

You can also run the test directly, that is, without using pytest, like so

.. code-block:: bash

    python examples/simple_dff/test_dff.py

This requires that you define the test to run in the testcase file itself.
For example, add the following code at the end:

.. code-block:: bash

    if __name__ == "__main__":
        test_simple_dff_runner()

API
===

The API of the Python runner is documented in section :ref:`api-runner`.
