.. _install:

************
Installation
************

Using cocotb requires :ref:`installation of pre-requisites<install-pre-requisites>` and
:ref:`installation of cocotb<installation-via-pip>` itself.
In this document, we are assuming that you already have a
:ref:`supported simulator<simulator-support>` available in ``PATH``.

.. _install-pre-requisites:

Pre-requisites
==============

Cocotb has the following requirements:

* Python 3.5+
* Python-dev packages
* GCC 4.8.1+ or Clang 3.3+ and associated development packages
* GNU Make
* A Verilog or VHDL simulator, depending on your RTL source code

.. versionchanged:: 1.4 Dropped Python 2 support

.. note:: In order to use a 32-bit simulator you need to use a 32-bit version of Python.


Windows
-------

`Conda <https://conda.io/>`_ is an open-source package and environment management system that we recommend for Windows.

Download and install `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ from https://conda.io/.
From a Command Prompt or the Windows PowerShell, use the following line to install a compiler (GCC or Clang) and GNU Make:

.. code-block:: bash

    conda install -c msys2 m2-base m2-make m2w64-toolchain libpython

.. seealso::

   For more installation options, please see `our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.


Linux - Debian/Ubuntu-based Systems
-----------------------------------

In a terminal, run

.. code-block:: bash

    sudo apt-get install make gcc g++ python3 python3-dev python3-pip
    sudo apt-get install swig  # optional, needed for one of the examples

.. seealso::

   For more installation options, please see `our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.


Linux - Red Hat-based Systems
-----------------------------

In a terminal, run

.. code-block:: bash

    sudo yum install make gcc gcc-c++ libstdc++-devel python3 python3-devel python3-pip
    sudo yum install swig  # optional, needed for one of the examples

.. seealso::

   For more installation options, please see `our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.


macOS
-----

We recommmend using the `Homebrew <https://brew.sh/>`_ package manager.
After installing it, run the following line in a terminal:

.. code-block:: bash

    brew install python icarus-verilog gtkwave

.. seealso::

   For more installation options, please see `our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.


.. _installation-via-pip:

Installation of cocotb
======================

.. versionadded:: 1.2

The **latest release** of cocotb can be installed by running

.. code-block:: bash

    pip install cocotb

.. warning::

    ``pip`` may belong to a different Python installation to what you expect.
    Use ``pip -V`` to check.
    If this prints "Python 2.7", use ``pip3`` or ``python3 -m pip`` in place of ``pip`` in the command shown.

For user-local installation, follow the `pip User Guide <https://pip.pypa.io/en/stable/user_guide/#user-installs/>`_.

If you want to install the **development version** of cocotb, :ref:`instructions are here<install-devel>`.

After installation, you should be able to execute ``cocotb-config``.
If it is not found, you need to append its location to the ``PATH`` environment variable.
This may happen when you use the ``--user`` option to ``pip``, in which case the location is documented :ref:`here <python:inst-alt-install-user>`.
