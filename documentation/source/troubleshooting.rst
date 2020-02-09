###############
Troubleshooting
###############

Simulation Hangs
================

Did you directly call a function that is decorated as a :class:`~cocotb.coroutine`,
i.e. without using :keyword:`await` or :keyword:`yield`?


Increasing Verbosity
====================

If things fail in the VPI/VHPI/FLI area, check your simulator's documentation to see if it has options to
increase its verbosity about what may be wrong. You can then set these options on the :command:`make` command line
as :make:var:`COMPILE_ARGS`, :make:var:`SIM_ARGS` or :make:var:`EXTRA_ARGS` (see :doc:`building` for details).
Moreover the scheduler activity can be enhanced by setting the variable :make:var:`COCOTB_SCHEDULER_DEBUG` to
one.


Attaching a Debugger
====================

C-Code
------

In order to give yourself time to attach a debugger to the simulator process before it starts to run,
you can set the environment variable :envvar:`COCOTB_ATTACH` to a pause time value in seconds.
If set, cocotb will print the process ID (PID) to attach to and wait the specified time before
actually letting the simulator run.

For the GNU debugger GDB, the command is :command:`attach <process-id>`.

Python
------

When executing the Makefile to run a cocotb test, a python shell interpreter is called from within the
VPI/VHPI/FLI library. Hence it is not possible to directly attach a python debugger to the python process being
part of the simulator that uses the aforementioned library.

To successfully debug your python code use the `remote_pdb`_ python package to create a :command:`pdb` instance
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
