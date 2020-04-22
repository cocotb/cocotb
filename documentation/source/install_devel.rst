.. _install-devel:

**********************************
Installing the Development Version
**********************************

To install the development version of cocotb on Windows, run the following:

.. code-block:: bash

    pip install --global-option build_ext --global-option --compiler=mingw32 https://github.com/cocotb/cocotb/archive/master.zip

For Linux and macOS, run:

.. code-block:: bash

    pip install https://github.com/cocotb/cocotb/archive/master.zip



FIXME: instructions for editable installation

FIXME: You may also need to use the ``--no-use-pep517`` option to ``pip``.

The instructions in :ref:`installation-via-pip` also apply.
