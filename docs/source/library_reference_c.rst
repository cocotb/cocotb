*********************
GPI Library Reference
*********************

cocotb contains a native library called :term:`GPI` (Generic Procedural Interface)
that is an abstraction layer for the VPI, VHPI, and FLI simulator interfaces.

.. image:: diagrams/svg/cocotb_overview.svg

The interaction between cocotb's Python and GPI is via a Python extension module called the :ref:`PyGPI <pygpi>`.

Environment Variables
=====================

.. envvar:: LIBPYTHON_LOC

    The absolute path to the Python library associated with the current Python installation;
    i.e. ``libpython.so`` or ``python.dll`` on Windows.
    This is determined with ``cocotb-config --libpython`` during build.

.. envvar:: GPI_EXTRA

    A comma-separated list of extra libraries that are dynamically loaded at runtime.
    A function from each of these libraries will be called as an entry point prior to elaboration,
    allowing these libraries to register system functions and callbacks.
    Note that :term:`HDL` objects cannot be accessed at this time.
    An entry point function must be named following a ``:`` separator,
    which follows an existing simulator convention.

    For example:

    * ``GPI_EXTRA=libnameA.so:entryA,libnameB.so:entryB`` will first load ``libnameA.so`` with entry point ``entryA`` , then load ``libnameB.so`` with entry point ``entryB``.

    .. versionchanged:: 1.4
        Support for the custom entry point via ``:`` was added.
        Previously ``:`` was used as a separator between libraries instead of ``,``.

    .. versionchanged:: 1.5
        Library name must be fully specified.
        This allows using relative or absolute paths in library names,
        and loading from libraries that `aren't` prefixed with "lib".
        Paths `should not` contain commas.

C API
=====

.. doxygenfile:: gpi.h
   :sections: brief detaileddescription define typedef enum

.. doxygengroup:: SimIntf
.. doxygengroup:: ObjQuery
.. doxygengroup:: ObjProps
.. doxygengroup:: SigProps
.. doxygengroup:: HandleIteration
.. doxygengroup:: SimCallbacks
