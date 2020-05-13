.. _install-devel:

**********************************
Installing the Development Version
**********************************

We are assuming here that you have :ref:`installed the prerequisites<install-prerequisites>`.

The instructions for installing the development version of cocotb vary depending on your operating system:

.. tabs::

   .. group-tab:: Windows

      The development version of cocotb can be installed globally by running

      .. code-block:: bash

          pip install --global-option build_ext --global-option --compiler=mingw32 https://github.com/cocotb/cocotb/archive/master.zip

      See also the `pip User Guide <https://pip.pypa.io/en/stable/user_guide/#user-installs/>`_.

   .. group-tab:: Linux and macOS

      The development version of cocotb can be installed globally by running

      .. code-block:: bash

          pip install https://github.com/cocotb/cocotb/archive/master.zip

      This requires administrator permissions.

      In order to install only for your current user, run

      .. code-block:: bash

          pip install https://github.com/cocotb/cocotb/archive/master.zip --user

      See also the `pip User Guide <https://pip.pypa.io/en/stable/user_guide/#user-installs/>`_.

.. warning::

    ``pip`` may belong to a different Python installation to what you expect.
    Use ``pip -V`` to check.
    If this prints "(python 2.7)", use ``pip3`` or ``python3 -m pip`` in place of ``pip`` in the command shown.

After installation, you should be able to execute ``cocotb-config``.
If it is not found, you need to append its location to the ``PATH`` environment variable.
This may happen when you use the ``--user`` option to ``pip``, in which case the location is documented :ref:`here <python:inst-alt-install-user>`.
