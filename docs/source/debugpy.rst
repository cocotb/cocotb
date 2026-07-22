.. _debugging-python-debugpy:

**********************************************
Remote Debugging Python with ``debugpy``
**********************************************

When running a cocotb simulation,
the Python interpreter is embedded inside the HDL simulator process
via the :term:`VPI`, :term:`VHPI`, or :term:`FLI` interface.
This means that Python is **not** launched as a standalone process by you,
and the simulator often interferes with ``stdin``,
making interactive debuggers like :mod:`pdb` difficult or impossible to use directly.

Microsoft's `debugpy <https://github.com/microsoft/debugpy>`__ implements the
`Debug Adapter Protocol (DAP) <https://microsoft.github.io/debug-adapter-protocol/>`__,
which allows a debugger **client** (e.g., VS Code, PyCharm) to connect to a running Python process over TCP.
This makes it possible to set breakpoints,
inspect variables,
and step through your cocotb test coroutines interactively — even inside a simulation.

.. note::
   ``debugpy`` works with any IDE that supports the Debug Adapter Protocol (DAP),
   including Visual Studio Code (with the Python extension),
   PyCharm Professional,
   and Eclipse with the PyDev plugin.

Installation
============

Install ``debugpy`` into your Python environment:

.. code-block:: bash

   pip install debugpy

Or, if you are using ``uv`` (the recommended cocotb development tool):

.. code-block:: bash

   uv add debugpy

Starting the Debug Server in a cocotb Test
==========================================

Inside your cocotb test file,
add the following snippet **before** the code you want to debug.
This starts a ``debugpy`` server that listens on TCP port ``5678``
and **waits** for a debugger client to connect before proceeding.

.. code-block:: python

   import cocotb
   import debugpy

   @cocotb.test()
   async def my_test(dut):
       # Start the debug server and wait for a client to attach.
       # The port number (5678) must match your IDE configuration.
       debugpy.listen(5678)
       print("Waiting for debugger to attach on port 5678...")
       debugpy.wait_for_client()
       debugpy.breakpoint()  # Optional: stop immediately after attach

       # --- Your test code below ---
       await cocotb.triggers.Timer(10, units="ns")
       assert dut.output.value == 1

.. warning::
   ``debugpy.wait_for_client()`` will block the simulation indefinitely until a debugger connects.
   Do not leave this in production test code.
   Remove it after debugging.

   If your simulation appears to hang,
   check whether a debugger client is connected.

Attaching from Visual Studio Code
===================================

1.  Open the repository folder in VS Code.

2.  Create or edit your ``.vscode/launch.json`` file to add a ``Python: Remote Attach`` configuration:

    .. code-block:: json

       {
         "version": "0.2.0",
         "configurations": [
           {
             "name": "cocotb: Attach debugpy",
             "type": "debugpy",
             "request": "attach",
             "connect": {
               "host": "localhost",
               "port": 5678
             },
             "pathMappings": [
               {
                 "localRoot": "${workspaceFolder}",
                 "remoteRoot": "."
               }
             ],
             "justMyCode": false
           }
         ]
       }

3.  Run your cocotb simulation normally (e.g., ``make SIM=icarus``).

4.  As soon as the simulation prints ``Waiting for debugger to attach on port 5678...``,
    switch to VS Code and press :kbd:`F5`
    (or select **Run > Start Debugging** and choose ``cocotb: Attach debugpy``).

5.  VS Code will connect and the simulation will resume.
    Breakpoints set in your test file will be hit normally.

Attaching from PyCharm
========================

1.  In PyCharm, go to **Run > Edit Configurations**.
2.  Click **+** and select **Python Debug Server**.
3.  Set:

    - **IDE host name**: ``localhost``
    - **Port**: ``5678``

4.  Click **OK**,
    then click the **Debug** button (green bug icon) to start the debug server client.
5.  Run your cocotb simulation.
    PyCharm will connect once the simulation reaches ``debugpy.listen()``.

Debugging Without Blocking (Non-Waiting Mode)
==============================================

If you do not want the simulation to pause and wait for a client,
you can remove :func:`debugpy.wait_for_client`.
In this case, the server starts in the background
and a debugger can attach at any time during the simulation run:

.. code-block:: python

   import debugpy

   # Start server in background (simulation continues immediately)
   debugpy.listen(5678)
   # No wait_for_client() here — attach at any time

   # Use debugpy.breakpoint() in your code where you want to stop.
   # Only hits if a client is connected at that moment.
   debugpy.breakpoint()

Choosing a Port
===============

The default port ``5678`` is used in the examples above.
If you need to run multiple simulations simultaneously,
or port ``5678`` is already in use,
choose a different port number and update your IDE configuration to match:

.. code-block:: python

   # Use port 9000 instead of the default 5678
   debugpy.listen(("localhost", 9000))

Troubleshooting
===============

**VS Code says "Connection refused"**
   The simulation has not yet reached the ``debugpy.listen()`` call.
   Wait until you see the ``Waiting for debugger...`` message in the terminal,
   then attach.

**Simulation hangs after attaching**
   Ensure you have called ``debugpy.wait_for_client()`` only when you intend to block.
   To add a safety timeout, use: ``debugpy.wait_for_client(timeout=30)``.

**Breakpoints are not hit**
   Ensure ``justMyCode`` is set to ``false`` in your VS Code ``launch.json``.
   Also verify that the ``pathMappings`` in ``launch.json``
   correctly maps your local workspace folder to the remote root (``"."``).

**``debugpy`` is not installed**
   Run ``pip install debugpy`` inside the same Python environment used by your simulator.
   You can verify the installation with:

   .. code-block:: bash

      python -c "import debugpy; print(debugpy.__version__)"

**Port already in use**
   Another process is using port ``5678``.
   Choose a different port and update both
   ``debugpy.listen()`` in your test file and the ``port`` in your IDE configuration.

See Also
========

- :doc:`troubleshooting` — General troubleshooting guide for cocotb
- :ref:`troubleshooting-attaching-debugger-c` — Attaching a C/C++ debugger with GDB
- :ref:`troubleshooting-attaching-debugger-python` — Using ``remote_pdb`` for terminal debugging
- `debugpy on GitHub <https://github.com/microsoft/debugpy>`__
- `VS Code Python Debugging Documentation <https://code.visualstudio.com/docs/python/debugging>`__
- `Debug Adapter Protocol Specification <https://microsoft.github.io/debug-adapter-protocol/>`__
