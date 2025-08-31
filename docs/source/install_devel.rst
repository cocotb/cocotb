.. _install-devel:

**********************************
Installing the Development Version
**********************************

.. note::

   If you want to follow the instructions on this page,
   make sure you are reading the
   `development version <https://docs.cocotb.org/en/development/install_devel.html>`_.

   Once you install the development version,
   you should keep reading the
   `matching documentation <https://docs.cocotb.org/en/development/>`_.

The development version of cocotb has different prerequisites
than the stable version (see below).
Namely, it requires the Python development headers and a C/C++ compiler.

* Python 3.6.2+
* Python development packages
* GCC 4.8.1+, Clang 3.3+ or Microsoft Visual C++ 14.21+ and associated development packages
* On Linux: A static build of the C++ standard library ``libstdc++``.
  Some distributions include the static library in their default packages (e.g. Debian/Ubuntu),
  others (e.g. Red Hat) require the installation of a package typically named ``libstdc++-static``.
* GNU Make
* A Verilog or VHDL simulator, depending on your :term:`RTL` source code

.. note:: Type checking cocotb code requires Python 3.11+.

The installation instructions vary depending on your operating system:

.. tab-set::

   .. tab-item:: Windows + Conda

      .. code-block::

         conda install -c msys2 m2-base m2-make

   .. tab-item:: Linux - Debian/Ubuntu

      In a terminal, run

      .. code-block:: bash

          sudo apt-get install make gcc g++ python3 python3-dev python3-pip

   .. tab-item:: Linux - Red Hat

      If you are using RHEL9, it might be necessary to add the CodeReady Linux Builder repository
      to be able to install ``libstdc++-static``.
      To add this repo, run in a terminal

      .. code-block:: bash

          sudo subscription-manager repos --enable codeready-builder-for-rhel-9-$(arch)-rpms

      Then, run

      .. code-block:: bash

          sudo yum install make gcc gcc-c++ libstdc++-devel libstdc++-static python3 python3-devel python3-pip

   .. tab-item:: macOS

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


Passing Flags to cocotb Library Build
=====================================

You may want to pass additional flags when building cocotb's C++ libraries.
These libraries are built during the ``pip install`` call when installing from a source distribution,
e.g. a local clone, from Github directly, or from an sdist tarball.

You can pass additional options to the library build process using the
`conventional variables <https://www.gnu.org/software/make/manual/html_node/Catalogue-of-Rules.html>`_
for C and C++ compilation and linking: ``CFLAGS``, ``CPPFLAGS``, and ``LDFLAGS`` when building with GCC or Clang,
and `CL <https://learn.microsoft.com/en-us/cpp/build/reference/cl-environment-variables>`_ when building with MSVC.

.. code-block:: shell

    $ CFLAGS="-O2 -g" LDFLAGS="-O2 -g" pip install git+https://github.com/cocotb/cocotb@master

.. note::

    ``CXXFLAGS``, ``LDLIBS`` are not supported by the distutils/pip build system.
