***************
Troubleshooting
***************

Simulation Hangs
================

Did you directly call an ``async def`` function without using :keyword:`await`;
or a :class:`~cocotb.coroutine` without using :keyword:`yield`?

If you want to exit cocotb and the simulator using :kbd:`Control-C` (the Unix signal ``SIGINT``) but this doesn't work,
you can try :kbd:`Control-\\` (the Unix signal ``SIGQUIT``).


Increasing Verbosity
====================

If things fail in the :term:`VPI`/:term:`VHPI`/:term:`FLI` area, check your simulator's documentation to see if it has options to
increase its verbosity about what may be wrong. You can then set these options on the :command:`make` command line
as :make:var:`COMPILE_ARGS`, :make:var:`SIM_ARGS` or :make:var:`EXTRA_ARGS` (see :doc:`building` for details).
If things fail from within Python, or coroutines aren't being called when you expect, the
:envvar:`COCOTB_SCHEDULER_DEBUG` variable can be used to (greatly) increase the verbosity of the scheduler.


.. _troubleshooting-attaching-debugger:

Attaching a Debugger
====================

.. _troubleshooting-attaching-debugger-c:

C and C++
---------

In order to give yourself time to attach a debugger to the simulator process before it starts to run,
you can set the environment variable :envvar:`COCOTB_ATTACH` to a pause time value in seconds.
If set, cocotb will print the process ID (PID) to attach to and wait the specified time before
actually letting the simulator run.

For the GNU debugger GDB, the command is ``attach <process-id>``.

.. _troubleshooting-attaching-debugger-python:

Python
------

When executing the Makefile to run a cocotb test, a Python shell interpreter is called from within the
:term:`VPI`/:term:`VHPI`/:term:`FLI` library.
Hence it is not possible to directly attach a Python debugger to the Python process being part of the simulator that uses the aforementioned library.
Using ``import pdb; pdb.set_trace()`` directly is also frequently not possible,
due to the way that simulators interfere with ``stdin``.

To successfully debug your Python code use the `remote_pdb`_ Python package to create a :command:`pdb` instance
accessible via a TCP socket:

.. _remote_pdb: https://pypi.org/project/remote-pdb/

1. In your code insert the line:

   .. code:: python

      from remote_pdb import RemotePdb; rpdb = RemotePdb("127.0.0.1", 4000)

2. Then before the line of code you want the debugger to stop the execution, add a breakpoint:

   .. code:: python

      rpdb.set_trace()  # <-- debugger stops execution after this line
      <your code line>  # <-- next statement being evaluated by the interpreter

3. Run the Makefile so that the interpreter hits the breakpoint line and *hangs*.
4. Connect to the freshly created socket, for instance through :command:`telnet`:

   .. code:: shell

      telnet 127.0.0.1 4000


Embedding an IPython shell
==========================

.. module:: cocotb.ipython_support

.. versionadded:: 1.4

A prebuilt test is included to easily launch an IPython shell in an existing design.

.. autofunction:: run_ipython

To embed a shell within an existing test, where it can inspect local variables, the :func:`embed` function can be used.

.. autofunction:: embed


.. _troubleshooting-make-vars:

Setting make variables on the command line
==========================================

When trying to set one of the make variables listed in :ref:`building` from the command line,
it is strongly recommended to use an environment variable, i.e.
``EXTRA_ARGS="..." make`` (for the ``fish`` and ``csh`` shells: ``env EXTRA_ARGS="..." make``)
and *not* ``make EXTRA_ARGS=...``.

This is because in the case of the discouraged ``make EXTRA_ARGS=...``,
if one of the involved Makefiles contains lines to assign (``=``) or append (``+=``) to :make:var:`EXTRA_ARGS` internally,
such lines will be ignored.
These lines are needed for the operation of cocotb however,
and having them ignored is likely to lead to strange errors.

As a side note,
when you need to *clear* a Makefile variable from the command line,
use the syntax ``make EXTRA_ARGS=``.

``GLIBCXX_3.4.XX`` not found
============================

This error can occur on Linux, and will raise ``ImportError: /some/libstdc++.so.6: version `GLIBCXX_3.4.XX' not found``.
This occurs because an older non-C++11 version of ``libstdc++`` is being loaded by the simulator or cocotb.
It is usually an issue with your environment, but sometimes can occur when using a very old version of certain simulators.

Check your environment
----------------------

To see if your environment is the issue, look at the value of the :envvar:`LD_LIBRARY_PATH` environment variable.
Ensure the first path in the colon-delimited list is the path to the ``libstdc++`` that shipped with the compiler you used to build cocotb.

.. code:: shell

    echo $LD_LIBRARY_PATH

This variable might be empty, in which case the loader looks in the system's libraries.
If the library you built cocotb with is not first, prepend that path to the list.

.. code:: shell

    export LD_LIBRARY_PATH=/path/to/newer/libraries/:$LD_LIBRARY_PATH

Check your simulator
--------------------

Sometimes, simulators modify the :envvar:`LD_LIBRARY_PATH` so they point to the libraries that are shipped with instead of the system libraries.
If you are running an old simulator, the packaged libraries may include a pre-C++11 ``libstdc++``.
To see if your simulator is modifying the :envvar:`LD_LIBRARY_PATH`, open the simulator up to an internal console and obtain the environment variable.

For example, with Mentor Questa and Cadence Xcelium, one could open a Tcl console and run the :command:`env` command to list the current environment.
The :envvar:`LD_LIBRARY_PATH` should appear in the list.

If the simulator does modify the :envvar:`LD_LIBRARY_PATH`, refer to the simulator documentation on how to prevent or work around this issue.

For example, Questa ships with GCC.
Sometimes that version of GCC is old enough to not support C++11 (<4.8).
When you install cocotb, :command:`pip` uses the system (or some other) compiler that supports C++11.
But when you try to run cocotb with the older Questa, it prepends the older libraries Questa ships with to :envvar:`LD_LIBRARY_PATH`.
This causes the older ``libstdc++`` Questa ships with to be loaded, resulting in the error message.
For Questa, you can use the ``-noautoldlibpath`` option to turn off the :envvar:`LD_LIBRARY_PATH` prepend to resolve this issue.


Using cocotb with more than one Python installation
===================================================

Users of cocotb with more than one installation of a single Python version (including ``conda env`` users)
must take care not to re-use cached versions of the installed cocotb package.
If this isn't done, running simulations fails with errors like ``libpython3.7m.so.1.0: cannot open shared object file: No such file or directory``.

Cocotb builds binary libraries during its installation process.
These libraries are tailored to the installation of Python used when installing cocotb.
When switching between Python installations, cocotb needs to be re-installed without using cached build artifacts, e.g. with ``pip install --no-cache-dir cocotb``.

On Linux distributions, setting ``LD_DEBUG=libs`` (example: ``LD_DEBUG=libs make SIM=verilator``) prints detailed output about which libraries are loaded from where.
On Mac OS, you can use ``DYLD_PRINT_LIBRARIES=1`` instead of ``LD_DEBUG=libs`` to get similar information.
On Windows, use `Process Explorer <https://docs.microsoft.com/en-us/sysinternals/downloads/process-explorer>`_.

Further details are available in :issue:`1943`.
