.. _install:

************
Installation
************

Using cocotb requires installation of prerequisites and installation of cocotb itself.
In this document, we are assuming that you already have a
:ref:`supported simulator<simulator-support>` available in ``PATH``.


.. _install-prerequisites:

Installation of Prerequisites
=============================

The current stable version of cocotb requires:

* Python 3.5+
* Python-dev packages
* GCC 4.8.1+ or Clang 3.3+ and associated development packages
* GNU Make
* A Verilog or VHDL simulator, depending on your :term:`RTL` source code

.. versionchanged:: 1.4 Dropped Python 2 support

.. note:: In order to use a 32-bit simulator you need to use a 32-bit version of Python.

The installation instructions vary depending on your operating system:

.. tabs::

   .. group-tab:: Windows

      `Conda <https://conda.io/>`_ is an open-source package and environment management system that we recommend for Windows.

      Download and install `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ from https://conda.io/.
      From an Anaconda Prompt, use the following line to install a compiler (GCC or Clang) and GNU Make:

      .. code-block::

         conda install -c msys2 m2-base m2-make m2w64-toolchain libpython

   .. group-tab:: Linux - Debian

      In a terminal, run

      .. code-block:: bash

          sudo apt-get install make gcc g++ python3 python3-dev python3-pip

   .. group-tab:: Linux - Red Hat

      In a terminal, run

      .. code-block:: bash

          sudo yum install make gcc gcc-c++ libstdc++-devel python3 python3-devel python3-pip

   .. group-tab:: macOS

      We recommmend using the `Homebrew <https://brew.sh/>`_ package manager.
      After installing it, run the following line in a terminal:

      .. code-block:: bash

           brew install python icarus-verilog gtkwave


.. _install-cocotb:
.. _installation-via-pip:

Installation of cocotb
======================

.. tabs::

   .. group-tab:: Windows

      The **latest release** of cocotb can be installed by running

      .. code-block:: bash

          pip install --global-option build_ext --global-option --compiler=mingw32 cocotb

   .. group-tab:: Linux - Debian

      The **latest release** of cocotb can be installed by running

      .. code-block:: bash

          pip install cocotb

   .. group-tab:: Linux - Red Hat

      The **latest release** of cocotb can be installed by running

      .. code-block:: bash

          pip install cocotb

   .. group-tab:: macOS

      The **latest release** of cocotb can be installed by running

      .. code-block:: bash

          pip install cocotb

.. note::

    If your user does not have permissions to install cocotb using the instructions above,
    try adding the ``--user`` option to ``pip``
    (see `the pip documentation <https://pip.pypa.io/en/stable/user_guide/#user-installs>`_).

.. warning::

    ``pip`` may belong to a different Python installation to what you expect.
    Use ``pip -V`` to check.
    If this prints "(python 2.7)", use ``pip3`` or ``python3 -m pip`` in place of ``pip`` in the command shown.

If you want to install the **development version** of cocotb, :ref:`instructions are here<install-devel>`.

After installation, you should be able to execute ``cocotb-config``.
If it is not found, you need to append its location to the ``PATH`` environment variable.
This may happen when you use the ``--user`` option to ``pip``, in which case the location is documented :ref:`here<python:inst-alt-install-user>`.


For more installation options, please see `our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.
