**********************
Writing cocotb Plugins
**********************

This guide explains how to write a custom Python plugin to extend existing cocotb capabilities.

cocotb gives its users a framework to build Python testbenches for hardware designs.

For example, it comes with default implementation of :class:`cocotb.regression.RegressionManager`
that handles execution of test functions decorated with :func:`cocotb.test`.

But Python world offers a wide choice of different testing frameworks with far more
advanced features that can help boost quality and productivity of created tests.
Like for example `pytest`_ with
`fixtures support <https://docs.pytest.org/en/stable/explanation/fixtures.html>`_,
`tests parametrization <https://docs.pytest.org/en/stable/example/parametrize.html>`_ and
`large number of existing plugins <https://docs.pytest.org/en/stable/reference/plugin_list.html>`_
that can be used in RTL verification as well.

cocotb plugin facility allows to integrate and use these existing testing frameworks
without sacrificing any of cocotb capabilities.

Creating Plugin Project
=======================

The best way to create our custom cocotb plugin is to use Python entry points available with
`package metadata <https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata>`_.

For that, we need to create a small standalone Python project for our plugin.
It requires only few files.

Example tree structure of plugin project:

.. code-block:: none

    <plugin-project>
    ├── pyproject.toml
    └── src
        └── <plugin-module-name>
            ├── __init__.py
            └── plugin.py

    3 directories, 3 files

Example content of ``pyproject.toml`` file:

.. code-block:: toml

    [project]
    name = "<plugin-package-name>"
    version = "0.1.0"
    dependencies = ["cocotb"]

    # https://packaging.python.org/en/latest/guides/tool-recommendations/#build-backends
    [build-system]
    requires = ["hatchling", "hatch-vcs"]
    build-backend = "hatchling.build"

Example content of ``plugin.py`` file:

.. code-block:: python

    """Plugin module."""

    import cocotb.handle  # NOTE: workaround for cocotb circular dependency
    from cocotb.regression import RegressionManager


    class MyRegressionManager(RegressionManager):
        def start_regression(self) -> None:
            print("My own tests regression manager for cocotb! Start hacking...")

            # Start default implementation of regression manager from cocotb or try to implement own
            super().start_regression()


    # cocotb_regression_manager function will be called automatically by cocotb plugin facility
    def cocotb_regression_manager() -> type[RegressionManager]:
        """Register new tests regression manager for cocotb."""
        return MyRegressionManager


Using Plugin in Projects
========================

To use cocotb plugin in our projects, we simple need to add it as dependency and
define it as part of ``[project.entry-points.cocotb]`` entry in ``pyproject.toml`` file.

Example content of ``pyproject.toml`` file in projects:

.. code-block:: toml

    [project]
    name = "<my-awesome-project>"
    version = "0.1.0"
    dependencies = ["cocotb", "<plugin-package-name>"]

    [project.entry-points.cocotb]
    plugin-name = "<plugin-module-name>.plugin"

List of Plugins
===============

* `pytest_cocotb <https://gitlab.com/tymonx/pytest-cocotb>`_ - Plugin to integrate `pytest`_ with cocotb.

.. _pytest: https://docs.pytest.org
