# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Generic option used as command line argument and entry in configuration file."""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

from pytest import OptionGroup, Parser

from cocotb_tools.pytest import env

PREFIXES: tuple[str, ...] = ("cocotb_", "gpi_", "pygpi_")


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
    """Representation of single cocotb option that can be set from
    configuration file, environment variable or command line."""

    def __init__(
        self,
        name: str,
        description: str,
        default: object | None = None,
        default_in_help: str | None = None,
        environment: str | None = None,
        **kwargs: object,
    ) -> None:
        """Create new instance of single option.

        Args:
            name: Name of option.
            description: Help description of option.
            default: Default value for option.
            default_in_help: Message used in option help instead of default value.
            environment: Name of environment variable.
            kwargs: Additional name arguments passed to :py:func:`argparse.ArgumentParser.add_argument`.
        """
        self.name: str = name
        self.description: str = description
        self.extra: dict[str, Any] = dict(kwargs)
        self.default: Any = default
        self.default_in_help: str | None = default_in_help
        self.environment: str = environment if environment else name.upper()

    def add_to_parser(self, parser: Parser, group: OptionGroup) -> None:
        argument: str = "--" + self.name.replace("_", "-")
        default: Any = self.default
        choices: tuple[str, ...] | None = self.extra.get("choices")
        argtype: type | None = self.extra.get("type")
        action: str | None = self.extra.get("action")
        nargs: str | None = self.extra.get("nargs")
        ini_type: IniType | None = None

        # Map command line argument to option in configuration file
        # Environment variable set by user can override default value for option
        if action == "store_true":
            default = env.as_bool(self.environment, default)
            ini_type = "bool"
        elif nargs:
            default = env.as_list(self.environment, default)
            ini_type = "paths" if argtype == Path else "args"
        elif argtype is int:
            default = env.as_int(self.environment, default)
            ini_type = "int"
        elif argtype is Path:
            default = env.as_path(self.environment, default)
            ini_type = "string"
        elif argtype is shlex.split:
            default = env.as_args(self.environment, default)
            ini_type = "args"
        elif choices:
            default = env.as_str(self.environment, default).lower()
            ini_type = "string"

            # Resolve values passed from environment variables
            if not default or default in choices:
                pass
            elif "yes" in choices and default in ("1", "y", "on", "true", "enable"):
                default = "yes"
            elif "no" in choices and default in ("0", "n", "off", "false", "disable"):
                default = "no"
            else:
                raise ValueError(
                    f"Invalid value '{default}' for environment variable {self.environment}. "
                    f"Expecting one of {(*choices,)}"
                )
        else:
            default = env.as_str(self.environment, default)
            ini_type = "string"

        # Use custom message or value in default
        default_in_help: Any = self.default_in_help if self.default_in_help else default

        # Add option entry to configuration files (pyproject.toml, pytest.ini, ...)
        parser.addini(
            self.name,
            help=f"Default value for {argument}",
            type=ini_type,
            default=default,
        )

        # Add option as command line argument
        group.addoption(
            argument,
            help=(
                f"{self.description}\n"
                f"Environment variable: {self.environment}\n"
                f"Default: {default_in_help}"
            ),
            **self.extra,
        )


def add_options_to_parser(parser: Parser, name: str, options: Iterable[Option]) -> None:
    """Add options to parser.

    Args:
        parser:  Pytest parser.
        name:    Name of group for options.
        options: List of options to be added to parser.
    """
    group: OptionGroup = parser.getgroup(name, description=f"{name} options")

    for option in options:
        option.add_to_parser(parser, group)


def is_cocotb_option(name: str) -> bool:
    """Check if provided name is a cocotb option.

    Args:
        name: Name of option (command line argument, entry from configuration file, ...).

    Returns:
        True if option is cococtb option. Otherwise False.
    """
    return any(name.startswith(prefix) for prefix in PREFIXES)
