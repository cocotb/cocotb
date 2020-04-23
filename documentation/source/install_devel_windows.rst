.. _install-devel-windows:

*******
Windows
*******

We are assuming you have installed the prerequisites as described :ref:`here <install-windows>`.

The development version of cocotb can be installed globally by running

.. code-block:: bash

    pip install --global-option build_ext --global-option --compiler=mingw32 https://github.com/cocotb/cocotb/archive/master.zip

This requires administrator permissions.

In order to install only for your current user, run

.. code-block:: bash

    pip install --global-option build_ext --global-option --compiler=mingw32 https://github.com/cocotb/cocotb/archive/master.zip --user

See also the `pip User Guide <https://pip.pypa.io/en/stable/user_guide/#user-installs/>`_.

.. include:: install_pip3_warning.rst

.. include:: install_after_check.rst
