.. _install:

************
Installation
************

.. note::
   If you want to install the **development version** of cocotb,
   `instructions are here <https://docs.cocotb.org/en/development/install_devel.html>`_.

Using cocotb requires installation of prerequisites and installation of cocotb itself.

Alternatively, you may use a package manager, see :ref:`install-package-manager`.

In this document, we are assuming that you already have a
:ref:`supported simulator<simulator-support>` available in :envvar:`PATH`.


.. _install-prerequisites:

Installation of Prerequisites
=============================

The current stable version of cocotb requires:

* Python 3.6.2+
* GNU Make 3+
* A Verilog or VHDL simulator, depending on your :term:`RTL` source code

.. versionchanged:: 1.7 Dropped requirement of Python development headers and C++ compiler for release versions.

.. versionchanged:: 1.6 Dropped Python 3.5 support

.. versionchanged:: 1.4 Dropped Python 2 support

.. note:: In order to use a 32-bit simulator you need to use a 32-bit version of Python.

.. note:: Type checking cocotb code requires Python 3.11+.

The installation instructions vary depending on your operating system:

.. tab-set::

   .. tab-item:: Windows

      We recommend users who are running Windows and who are more comfortable with a Unix shell,
      or who have legacy Makefile-based projects,
      to use Windows Subsystem for Linux (WSL).
      After installing WSL and a supported Linux distribution, follow the Linux installation instructions for cocotb.

      `Conda <https://conda.io/>`_ is an open-source package and environment management system that we recommend for users who are more comfortable with native Windows development.
      Download and install `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ from https://conda.io/.
      From an Anaconda Prompt, use the following line to install a compiler (GCC or Clang) and GNU Make:

      .. code-block::

         conda install -c msys2 m2-base m2-make

   .. tab-item:: Linux - Debian

      In a terminal, run

      .. code-block:: bash

          sudo apt-get install make python3 python3-pip libpython3-dev

   .. tab-item:: Linux - Red Hat

      In a terminal, run

      .. code-block:: bash

          sudo yum install make python3 python3-pip python3-libs

   .. tab-item:: macOS

      We recommend using the `Homebrew <https://brew.sh/>`_ package manager.
      After installing it, run the following line in a terminal:

      .. code-block:: bash

           brew install python

.. _install-cocotb:
.. _installation-via-pip:

Installation of cocotb
======================

.. only:: is_release_build

    You are reading the documentation for cocotb |version|.
    To install this version, or any later compatible version, run

    .. parsed-literal::

        pip install "cocotb~=\ |version|\ "

.. only:: not is_release_build

    The latest **stable version** of cocotb can be installed by running

    .. code-block:: bash

        pip install cocotb

.. note::

    If your user does not have permissions to install cocotb using the instructions above,
    try adding the ``--user`` option to :command:`pip`
    (see `the pip documentation <https://pip.pypa.io/en/stable/user_guide/#user-installs>`_).

.. warning::

    :command:`pip` may belong to a different Python installation to what you expect.
    Use ``pip -V`` to check.
    If this prints "(python 2.7)", use :command:`pip3` or ``python3 -m pip`` in place of :command:`pip` in the command shown.

.. _install-package-manager:

Alternative installation using a Package Manager
================================================

The installation instructions vary depending on your package manager:

.. tab-set::

   .. tab-item:: Guix

      In a terminal, run

        .. code-block:: bash

	        guix install python-cocotb

Post installation
=================

After installation, you should be able to execute :command:`cocotb-config`.
If it is not found, you need to append its location to the :envvar:`PATH` environment variable.

For more installation options, please see `our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.
