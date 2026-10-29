.. _separating-logs:

******************************************
Separating cocotb and Simulator Log Output
******************************************

When a test runs, cocotb's own log messages and the simulator's output
share a single stream.
This is fine interactively,
but it makes life hard when you want to keep the simulator transcript free of cocotb chatter or vice versa.

This guide shows users how to configure cocotb's loggers to output to a file.

Why the two are mixed
=====================

cocotb emits its messages through the Python :mod:`python:logging` module.
:func:`cocotb.logging.default_config` configures the root logger to write to
standard output,
and every cocotb logger propagates its records up to that root logger.

The simulator writes its own output, such as that produced by ``$display``,
directly to standard output.
It never passes through Python's :mod:`python:logging` machinery,
so it cannot be redirected by configuring a logger.

Redirecting cocotb's log
========================

Because every cocotb logger propagates to the root logger,
you do not need to touch the individual cocotb loggers.
Remove the handlers cocotb installed on the root logger,
and register your own instead.
cocotb's logs then flow through your handler to wherever that handler is configured to write to,
while the simulator's output is left on standard output untouched.

.. code-block:: python

    import logging

    from cocotb.logging import SimLogFormatter

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler("cocotb.log", mode="w")
    file_handler.setFormatter(SimLogFormatter())
    root_logger.addHandler(file_handler)

Place this at module level in your test module so that it runs when cocotb imports the module.

Using :class:`~cocotb.logging.SimLogFormatter` keeps the simulation timestamp
and the familiar cocotb layout in the redirected output.
A plain :class:`python:logging.Formatter` works too,
but the simulation time is then lost unless the format string refers to it.

To send cocotb's output somewhere other than a file,
register a different :class:`python:logging.Handler`.
For example, a :class:`python:logging.StreamHandler` on :data:`python:sys.stderr`
keeps cocotb's messages on the console
while still separating them from the simulator's output on standard output,
which is convenient when redirecting one stream to a file from the shell.

.. note::
   A handful of start-up messages are still written to standard output.
   These come from the ``gpi`` and ``pygpi`` loggers,
   and from ``cocotb.initialize`` reporting the cocotb and simulator versions.
   They are emitted before cocotb imports your test module,
   so they are logged before the handler above is installed.
   The exact count depends on the simulator,
   so treat the remaining start-up lines as expected rather than fixed.

.. seealso::

   :ref:`rotating-logger` keeps the redirected output in rotating files,
   and :ref:`logging-reference-section` documents the logging API.
