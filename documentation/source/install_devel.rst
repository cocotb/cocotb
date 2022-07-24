.. _install-devel:

**********************************
Installing the Development Version
**********************************

.. note::

   If you want to follow the instructions on this page,
   make sure you are reading its
   `latest version <https://docs.cocotb.org/en/latest/install_devel.html>`_.

   Once you install the development version,
   you should keep reading the
   `matching documentation <https://docs.cocotb.org/en/latest/>`_.

The development version of cocotb has different prerequisites
than the stable version (see below).
Namely, it requires the Python development headers and a C/C++ compiler.

* Python 3.6+
* Python development packages
* GCC 4.8.1+, Clang 3.3+ or Microsoft Visual C++ 14.21+ and associated development packages
* GNU Make
* A Verilog or VHDL simulator, depending on your :term:`RTL` source code

The installation instructions vary depending on your operating system:

.. tabs::

   .. group-tab:: Windows + Conda

      .. code-block::

         conda install -c msys2 m2-base m2-make

   .. group-tab:: Linux - Debian

      In a terminal, run

      .. code-block:: bash

          sudo apt-get install make gcc g++ python3 python3-dev python3-pip

   .. group-tab:: Linux - Red Hat

      In a terminal, run

      .. code-block:: bash

          sudo yum install make gcc gcc-c++ libstdc++-devel python3 python3-devel python3-pip

   .. group-tab:: macOS

      .. code-block:: bash

           brew install python


The development version of cocotb can be installed by running

.. code-block:: bash

    pip install git+https://github.com/cocotb/cocotb@master

.. note::

    If your user does not have permissions to install cocotb using the instructions above,
    try adding the ``--user`` option to ``pip``
    (see `the pip documentation <https://pip.pypa.io/en/stable/user_guide/#user-installs>`_).

.. warning::

    ``pip`` may belong to a different Python installation to what you expect.
    Use ``pip -V`` to check.
    If this prints "(python 2.7)", use ``pip3`` or ``python3 -m pip`` in place of ``pip`` in the command shown.

After installation, you should be able to execute ``cocotb-config``.
If it is not found, you need to append its location to the ``PATH`` environment variable.
This may happen when you use the ``--user`` option to ``pip``, in which case the location is documented :ref:`here<python:inst-alt-install-user>`.
