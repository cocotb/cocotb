# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Handling of pytest plugin options.

Option precedence (from highest to lowest):

1. Command-line argument ``--cocotb-*`` when invoking the ``pytest`` command.
2. Configuration entry ``cocotb_*`` defined in a pytest configuration file (e.g., ``pyproject.toml``).
3. Environment variable ``COCOTB_*``.
4. Default option value.
"""

from __future__ import annotations

import shlex
import textwrap
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Literal

from pytest import Config, OptionGroup

from cocotb_tools import _env

#: See https://docs.pytest.org/en/stable/reference/reference.html#pytest.Parser.addini
IniType = Literal[
    "string",
    "paths",
    "pathlist",
    "args",
    "linelist",
    "bool",
    "int",
    "float",
]


class Option:
    """Representation of a single cocotb option.

    An option can be configured via a configuration file (e.g., ``pyproject.toml``), an environment variable, or a command-line argument.
    """

    def __init__(
        self,
        name: str,
        description: str,
        default: Any = None,
        default_in_help: object = None,
        **kwargs: Any,
    ) -> None:
        """Create a new instance of a plugin option.

        Args:
            name: The name of the option.
            description: A description of the option for help messages.
            default: The default value for the option.
            default_in_help: A custom string to display in the help message instead of the default value.
            **kwargs: Additional keyword arguments passed directly to the :meth:`argparse.ArgumentParser.add_argument` method.
        """
        self.name: str = name
        self.kwargs: Mapping[str, Any] = kwargs
        self.default: Any = default
        self.default_in_help: object = default_in_help
        self.description: str = description

    def add_to_group(self, group: OptionGroup) -> None:
        """Add the plugin option to the pytest options parser.

        Args:
            group: The pytest OptionGroup to which this option will be added.
        """
        kind: object = self.kwargs.get("type")
        nargs: int | str | None = self.kwargs.get("nargs")
        action: str | None = self.kwargs.get("action")
        default: Any = self.default
        choices: Iterable[object] | None = self.kwargs.get("choices")
        argument: str = self.argument
        environment: str = self.environment

        ini_type: IniType

        # Map command line argument to option in configuration file
        # Environment variable set by user can override default value for option
        if action == "store_true":
            default = _env.as_bool(environment, default)
            ini_type = "bool"
        elif nargs and nargs != "?":
            default = _env.as_list(environment, default)

            if kind is Path:
                ini_type = "paths"
                default = [Path(value) for value in default]
            else:
                ini_type = "args"
        elif kind is int:
            default = _env.as_int(environment, default)
            ini_type = "int"
        elif kind is Path:
            default = Path(_env.as_str(environment, default))
            ini_type = "string"
        elif kind is shlex.split:
            default = _env.as_args(environment, default)
            ini_type = "args"
        elif choices:
            default = _env.as_str(environment, default).lower()
            ini_type = "string"

            if default and default not in choices:
                raise ValueError(
                    f"Invalid value '{default}' for environment variable {environment}. "
                    f"Expecting one of {(*choices,)}"
                )
        else:
            default = _env.as_str(environment, default)
            ini_type = "string"

        group.addoption(argument, help=self.help, **self.kwargs)

        if group.parser:
            group.parser.addini(
                name=self.name,
                type=ini_type,
                help=f"Default value for {argument}",
                default=default,
            )

    @property
    def environment(self) -> str:
        """The name of the environment variable associated with the option."""
        return self.name.upper()

    @property
    def argument(self) -> str:
        """The name of the command-line argument associated with the option."""
        return f"--{self.name.replace('_', '-')}"

    @property
    def help(self) -> str:
        """The formatted help text for the option."""
        entries: list[str] = [
            textwrap.dedent(self.description),
            f"Configuration option: ``{self.name}``",
            f"Environment variable: :envvar:`{self.environment}`",
        ]

        if self.default_in_help:
            entries.append(f"Default value: {self.default_in_help}")

        elif self.default or isinstance(self.default, int):
            entries.append(f"Default value: ``{self.default}``")

        return "\n\n".join(entries)


def populate_ini_options(config: Config, options: Iterable[Option]) -> None:
    """Populate INI options to :attr:`pytest.Config.option`."""
    for option in options:
        name: str = option.name
        value: Any = config.getoption(name)

        # Get option value from pytest configuration file or environment variable
        if value is None or value is False:
            setattr(config.option, name, config.getini(name))
