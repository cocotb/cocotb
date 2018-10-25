###############
Troubleshooting
###############

Increasing Verbosity
====================

If things fail in the VPI/VHPI/FLI area, check your simulator's documentation to see if it has options to 
increase its verbosity about what may be wrong. You can then set these options on the ``make`` command line
as ``COMPILE_ARGS``, ``SIM_ARGS`` or ``EXTRA_OPTS`` (see :doc:`building` for details).


Attaching a Debugger
====================

In order to give yourself time to attach a debugger to the simulator process before it starts to run,
you can set the environment variable ``COCOTB_ATTACH`` to a pause time value in seconds.
If set, Cocotb will print the process ID (PID) to attach to and wait the specified time before 
actually letting the simulator run.

For the GNU debugger GDB, the command is ``attach <process-id>``.
