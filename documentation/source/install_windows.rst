.. _install-windows:

*******
Windows
*******

.. include:: install_prerequisites_common.rst

`Conda <https://conda.io/>`_ is an open-source package and environment management system that we recommend for Windows.

Download and install `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ from https://conda.io/.
From a Command Prompt or the Windows PowerShell, use the following line to install a compiler (GCC or Clang) and GNU Make:

.. code-block:: bash

    conda install -c msys2 m2-base m2-make m2w64-toolchain libpython

.. include:: install_cocotb_windows.rst
