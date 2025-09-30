# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Factory to create other objects."""

import logging
import sys
from importlib import import_module
from typing import Any, Callable

# https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/#using-package-metadata
if sys.version_info < (3, 10):
    import importlib_metadata as metadata
else:
    from importlib import metadata


_logger = logging.getLogger(__name__)


class Factory:
    """Object to create other objects."""

    def __init__(self):
        """Create new instance of factory."""
        self._plugins = [
            import_module(entry_point.value)
            for entry_point in metadata.entry_points(group="cocotb")
        ]

    def create(self, cls, *args, plugin_function: str = "", **kwargs) -> object:
        """Create new object of requested class type.

        It can be overload by defining `cocotb` entry point in `pyproject.toml` file:

        .. code-block:: toml

            [project.entry-points.cocotb]
            <plugin-name> = "<python-module-name>"

        And by defining `plugin_function` in `<python-module-name>`
        that will return new extended class of `cls`.

        .. code-block:: python

            import cocotb.handle
            from cocotb.regression import RegressionManager


            class MyRegressionManager(RegressionManager):
                pass


            def cocotb_regression_manager() -> type[RegressionManager]:
                return MyRegressionManager

        Args:
            cls: Requested class type of object to be created by factory.

            args: Additional positional argument(s) passed directory to class constructor.

            plugin_function: Name of plugin function that returns requested class type used by factory to create object.
                If not provided, default is combination of `cocotb_` prefix with snake case of class type name.
                Example: `cocotb_regression_manager`.

            kwargs: Additional named argument(s) passed directory to class constructor.

        Returns:
            New object of requested class type, default implementation or from plugin.
        """
        obj: Any = None

        if not plugin_function:
            # Compose plugin function name
            # Example: RegressionManager -> cocotb_regression_manager
            plugin_function = "cocotb" + "".join(
                "_" + c.lower() if c.isupper() else c for c in cls.__name__
            )

        for plugin in self._plugins:
            # Specific plugin function was not provided, try with next plugin
            if not hasattr(plugin, plugin_function):
                continue

            # Get class type needed to create new object by calling plugin function
            function: Callable[[], Any] = getattr(plugin, plugin_function)
            class_type: Callable[..., Any] | type | None = function()

            # Class was not provided, try with next plugin
            if not class_type:
                continue

            # Create object using class constructor or assign it as object
            if isinstance(class_type, type):
                obj = class_type(*args, **kwargs)
            else:
                obj = class_type  # already created object, assign it as is

            _logger.debug(
                "Created new instance of %s from plugin function %s.%s",
                type(obj),
                plugin.__name__,
                plugin_function,
            )

            if not isinstance(obj, cls):
                _logger.fatal(
                    "Plugin function %s.%s must return extended class from %s",
                    plugin.__name__,
                    plugin_function,
                    cls,
                )

            break

        if not obj:
            obj = cls(*args, **kwargs)
            _logger.debug("Created new instance of %s", type(obj))

        return obj
