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

:command:`pip` is the officially supported and recommended package manager for installing the development version of cocotb.
Currently there are no alternative package managers that provide the development version of cocotb.
Below are the instructions for installing the development version of cocotb using :command:`pip`.


Install with ``pip``
====================


Install Prerequisites
---------------------

The development version of cocotb requires building C++ extensions.
This requires Python development headers, a C++ compiler, and C++ development libraries.

* Python 3.9+
* libpython 3.9+ to match the executable Python version
* Python development packages
* GCC 4.8.1+, Clang 3.3+ or Microsoft Visual C++ 14.21+ and associated development packages
* On Linux: A static build of the C++ standard library ``libstdc++``.
  Some distributions include the static library in their default packages (e.g. Debian/Ubuntu),
  others (e.g. Red Hat) require the installation of a package typically named ``libstdc++-static``.

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


Install cocotb
--------------

The development version of cocotb can be installed by running the following command:

.. code-block:: bash

    pip install git+https://github.com/cocotb/cocotb@master

Alternatively, if you have cloned the cocotb repository locally, you can install it by running:

.. code-block:: bash

    pip install ./path/to/cocotb

For testing Python changes without reinstalling, you can use the editable install option.
This requires that you have cloned the cocotb repository locally.

.. code-block:: bash

    pip install -e ./path/to/cocotb

.. note::

    If your user does not have permissions to install cocotb using the instructions above,
    try adding the ``--user`` option to ``pip``
    (see `the pip documentation <https://pip.pypa.io/en/stable/user_guide/#user-installs>`_).

.. warning::

    ``pip`` may belong to a different Python installation to what you expect.
    Use ``pip -V`` to check.
    If this prints "(python 2.7)", use ``pip3`` or ``python3 -m pip`` in place of ``pip`` in the command shown.


Passing Flags to C++ Library Builds
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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


Verify Installation
-------------------

After installation, you should be able to execute the following command:

.. code-block:: bash

    cocotb-config --version

If the command is not found, you need to append its location to the ``PATH`` environment variable.

Verify the version printed matches the version you intended to install.
