*********************
GPI Library Reference
*********************

cocotb contains a native library called :term:`GPI` (Generic Procedural Interface)
that is an abstraction layer for the VPI, VHPI, and FLI simulator interfaces.

.. image:: diagrams/svg/cocotb_overview.svg

The interaction between cocotb's Python and GPI is via a Python extension module called the :ref:`PyGPI <pygpi>`.

Environment Variables
=====================

.. envvar:: GPI_USERS

    A list of native libraries to load, and optionally functions in those libraries to call,
    once the GPI is initialized.

    This list is ``;``-separated.
    Each element of the list contains a path to a library to load.
    These paths can be full paths (e.g. ``/usr/local/lib/libstuff.so``), in which case the exact library will be loaded,
    or the basename (e.g. ``libstuff.so``), in which case your operating system's dynamic library lookup will be used.

    Optionally, after the path in each element, a function in that library to call can be specified by name
    by suffixing the path with a ``,`` character followed by the function name.

    For example:

    * ``GPI_USERS=/usr/local/lib/libstuff.so;libotherstuff.so,entry_func``

    .. attention::
        This means that paths which contain the characters ``;`` and ``,`` cannot be used in this variable.
        Instead of using a full path, use the basename, and use environment variables like ``PATH`` or ``LD_LIBRARY_PATH``
        to modify your operating system's library search path.

    When using the :ref:`building` or :ref:`api-runner` this defaults to load ``libpython`` and then the PyGPI entry point.
    You can get the default PyGPI entry point at other times by calling ``cocotb-config --pygpi-entry-point`` from the shell
    or :func:`cocotb_tools.config.pygpi_entry_point` from Python.

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
.. doxygengroup:: Logging
