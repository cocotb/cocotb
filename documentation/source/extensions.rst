*************************
Writing cocotb extensions
*************************

This guide explains how to write cocotb extensions, with a focus on the conventions that should be followed.

Cocotb gives its users a framework to build Python testbenches for hardware designs.
But sometimes the functionality provided by cocotb is too low-level.
One common example are bus drivers and monitors:
instead of creating a bus adapter from scratch for each new project, wouldn't it be nice to share this component, and build on top it?
In the verification world, such extensions are often called "verification IP" (VIP).

In cocotb, such functionality can be packaged and distributed as extensions.
Technically, cocotb extensions are normal Python packages, and all standard Python packaging and distribution techniques can be used.
Additionally, the cocotb community has agreed on a set of conventions to make extensions easier to use and to discover.

.. _extensions-naming-conventions:

Naming conventions
==================

Cocotb extensions are normal Python modules which follow these naming conventions.

Assuming an extension named ``EXTNAME`` (all lower-case),

- the package is in the ``cocotbext.EXTNAME`` namespace, and
- the distribution (package) name is prefixed with ``cocotbext-EXTNAME``.

Example:
An SPI bus extension might be packaged as ``cocotbext-spi``, and its functionality would live in the ``cocotbext.spi`` namespace.
The module can then be installed with ``pip3 install cocotbext-spi``, and used with ``import cocotbext.spi``.

Types of cocotb extensions
==========================

For some types of cocotb extensions we have developed conventions which go beyond naming.
These conventions help to achieve a consistent behavior across extensions of the same type.

Bus extensions
--------------

A cocotb extension which interacts with a bus or an interface (such as SPI or AXI) should build on top of a common set of classes to provide a uniform interface for its users.
Typically, a bus extension provides three pieces of functionality:
an abstraction of the bus itself, a bus driver, and a bus monitor.

A bus driver is the "active" part, it drives the signals that make up the bus to request reads or writes from the bus.
A bus monitor is the "passive" part, it observes signal changes on the bus and assigns meaning to them.
Monitors can also check the bus behavior against a standard to ensure no invalid states are being observed.

The signals which make up the bus should be grouped in a class inheriting from :class:`cocotb_bus.bus.Bus`.
Bus drivers should inherit from the :class:`cocotb_bus.drivers.BusDriver` class.
Bus monitors should inherit from the :class:`cocotb_bus.monitors.BusMonitor` class.

Packaging extensions
====================

To package a cocotb extension as Python package follow the :ref:`extensions-naming-conventions`, and the `normal Python packaging rules <https://packaging.python.org/tutorials/packaging-projects/>`_.
Extensions namespaced packages, implemented using the `native namespacing <https://packaging.python.org/guides/packaging-namespace-packages/#native-namespace-packages>`_ approach discussed in :pep:`420`.
The module file hierarchy should be as follows (replace ``EXTNAME`` with the name of the extension, e.g. ``spi``).

.. code-block::

  # file structure of the cocotbext-EXTNAME repository
  ├── cocotbext/
  │   │   # No __init__.py here.
  │   └── EXTNAME/
  │       └── __init__.py
  ├── README.md
  └── setup.py

The Python source code should go into the :file:`EXTNAME` directory, next to the :file:`__init__.py` file.
All packaging metadata goes into :file:`setup.py`.

.. code-block:: python3

  # Minimal setup.py. Extend as needed.
  from setuptools import setup, find_namespace_packages

  setup(name = 'cocotbext-EXTNAME',
        version = '0.1',
        packages = find_namespace_packages(include=['cocotbext.*']),
        install_requires = ['cocotb'],
        python_requires = '>=3.6',
        classifiers = [
          "Programming Language :: Python :: 3",
          "Operating System :: OS Independent",
          "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
          "Framework :: cocotb"])

With this file structure in place the cocotb extension can be installed through ``pip`` in development mode ::

  $ python3 -m pip install -e .

Once the extension has been `uploaded to PyPi <https://packaging.python.org/tutorials/packaging-projects/#uploading-the-distribution-archives>`_, it can be installed by name.

.. code-block: command

  $ python3 -m pip install cocotbext-EXTNAME

To use the functionality in the extension module, import it into your testbench.

.. code-block:: python3

  # Examples for importing (parts of) the extension
  import cocotbext.EXTNAME
  from cocotbext import EXTNAME
  from cocotbext.EXTNAME import MyVerificationClass

Code hosting
============

The source code of cocotb extensions can be hosted anywhere.
If authors wish to do so, extensions can also be hosted on GitHub in the `cocotb GitHub organization <https://github.com/cocotb>`_ (e.g. ``github.com/cocotb/cocotbext-EXTNAME``).
Please file a `GitHub issue in the cocotb repository <https://github.com/cocotb/cocotb/issues>`_ if you'd like to discuss that.

Note that hosting extensions within the cocotb organization is decided on a case-by-case basis by the cocotb maintainers.
At least, a cocotb-hosted extension needs to fulfill the following requirements:

* It needs tests that can be run in order to see that the extension works
  and continues to work as cocotb itself changes, especially when a new release is upcoming.
* It needs documentation (preferably in Sphinx) so that users know how to use the extension.
* We must have access to the PyPi project so that we can continue to upload new releases
  in case the extension maintainer ("Owner") becomes unresponsive.
