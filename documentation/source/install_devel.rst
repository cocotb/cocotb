.. _install-devel:

**********************************
Installing the Development Version
**********************************

To install the development version of cocotb on **Windows**, run the following:

.. code-block:: bash

    pip install --global-option build_ext --global-option --compiler=mingw32 https://github.com/cocotb/cocotb/archive/master.zip

For **Linux** and **macOS**, run:

.. code-block:: bash

    pip install https://github.com/cocotb/cocotb/archive/master.zip

The instructions in :ref:`installation-via-pip` also apply.

For more installation options, please see `our Wiki <https://github.com/cocotb/cocotb/wiki/Tier-2-Setup-Instructions>`_.


FIXME: add instructions for editable installation

FIXME: add "You may also need to use the ``--no-use-pep517`` option to ``pip``." if...
