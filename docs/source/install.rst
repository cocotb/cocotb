.. _install:

************
Installation
************

.. note::
   If you want to install the **development version** of cocotb,
   `instructions are here <https://docs.cocotb.org/en/development/install_devel.html>`_.

:command:`pip` is the officially supported and recommended package manager for installing cocotb.
cocotb is also packaged by third parties to support installation via alternative package managers; see :ref:`install-package-manager` for details.
For more installation options, please visit `our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.


Install with ``pip``
====================


.. _install-prerequisites:

Install Prerequisites
---------------------

The current stable version of cocotb requires:

* Python 3.9+
* libpython 3.9+ which matches the Python version

The installation instructions vary depending on your operating system:

.. tab-set::

   .. tab-item:: Windows - Conda

      We recommend users who are more comfortable with native Windows development to use `Conda <https://conda.io/>`_.
      Conda is an open-source package and environment management system available on Windows.

      Download and install `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ from https://conda.io/.
      From an Anaconda Prompt, use the following line to install a compiler (GCC or Clang) and GNU Make:

      .. code-block:: bash

          conda install -c msys2 m2-base m2-make

   .. tab-item:: Windows - WSL

      We recommend users who are running Windows and who are more comfortable with a Unix shell,
      or who have legacy Makefile-based projects,
      to use Windows Subsystem for Linux (WSL).

      Follow the `Microsoft WSL installation guide <https://docs.microsoft.com/en-us/windows/wsl/install>`_ to install WSL
      with a :ref:`supported Linux distribution <supported-linux-distributions>`.
      Then follow the appropriate Linux installation instructions for cocotb.

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

Install cocotb
--------------

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


Verify Installation
-------------------

After installation, you should be able to execute the following command:

.. code-block:: bash

    cocotb-config --version

If the command is not found, you need to append its location to the ``PATH`` environment variable.

Verify the version printed matches the version you intended to install.


.. _install-package-manager:

Installation via Alternative Package Managers
=============================================

.. tab-set::

   .. tab-item:: Guix

      In a terminal, run

        .. code-block:: bash

	        guix install python-cocotb
