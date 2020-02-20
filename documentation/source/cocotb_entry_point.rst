
.. _custom-entry-point:

******************
Cocotb Entry Point
******************

By default, when cocotb is loaded, it perfoms some basic initialization and starts the regression manager.
However, there are many reasons why a user might want to do something different:

* select an alternative regression system
* override cocotb initializations
* experiment

To support this, the environment variable :envvar:`COCOTB_ENTRY` can be used to specify an alternative Python module and function to load after the Python interpreter has been initialized.

.. warning:: This is intended for advanced users only

.. versionadded:: 1.4

How It Works
============

Once the Python/GPI ``embed`` library is loaded, it does the following:

- starts the Python interpreter
- loads the ``cocotb`` module
- calls the ``_initialise_testbench`` function in the ``cocotb`` module
- ``_initialise_testbench`` starts the regression manager.

The :envvar:`COCOTB_ENTRY` variable allows the user to load a module other than ``cocotb``, and run an entry function other than ``_initialise_testbench``.
See the documentation for :envvar:`COCOTB_ENTRY` for details on the entry point specification.

Entry Point Interface Requirements
==================================

The Python/GPI ``embed`` library expects the following functions to be implemented in the entry module. The names are required.

.. py:function:: _sim_event(level: int, message: str) -> None

Finally, there is the entry function itself.
An entry function is not required to be named the same, and an entry module can contain multiple entry functions.

.. py:function:: _main(argv: List[str]) -> None

Entry functions take an argument list, much like any Python ``main`` function, that returns nothing. If the entry function encounters an error, it should raise an exception.
