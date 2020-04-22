Installation of cocotb
======================

.. versionadded:: 1.2

The **latest release** of cocotb can be installed by running

.. code-block:: bash

    pip install cocotb

.. warning::

    ``pip`` may belong to a different Python installation to what you expect.
    Use ``pip -V`` to check.
    If this prints "Python 2.7", use ``pip3`` or ``python3 -m pip`` in place of ``pip`` in the command shown.

For user-local installation, follow the `pip User Guide <https://pip.pypa.io/en/stable/user_guide/#user-installs/>`_.

If you want to install the **development version** of cocotb, :ref:`instructions are here<install-devel>`.

After installation, you should be able to execute ``cocotb-config``.
If it is not found, you need to append its location to the ``PATH`` environment variable.
This may happen when you use the ``--user`` option to ``pip``, in which case the location is documented :ref:`here <python:inst-alt-install-user>`.
