# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Generic option used as command line argument and entry in configuration file."""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Literal

from pytest import Config, OptionGroup, Parser

from cocotb_tools import _env

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

    @property
    def argument(self) -> str:
        """Command line argument."""
        return "--" + self.name.replace("_", "-")

    def add_to_parser(self, parser: Parser, group: OptionGroup) -> None:
        argument: str = self.argument
        default: Any = self.default
        choices: tuple[str, ...] | None = self.extra.get("choices")
        argtype: type | None = self.extra.get("type")
        action: str | None = self.extra.get("action")
        nargs: str | None = self.extra.get("nargs")
        ini_type: IniType | None = None

        # Map command line argument to option in configuration file
        # Environment variable set by user can override default value for option
        if action == "store_true":
            default = _env.as_bool(self.environment, default)
            ini_type = "bool"
        elif nargs:
            default = _env.as_list(self.environment, default)
            ini_type = "paths" if argtype == Path else "args"
        elif argtype is int:
            default = _env.as_int(self.environment, default)
            ini_type = "int"
        elif argtype is Path:
            default = _env.as_path(self.environment, default)
            ini_type = "string"
        elif argtype is shlex.split:
            default = _env.as_args(self.environment, default)
            ini_type = "args"
        elif choices:
            default = _env.as_str(self.environment, default).lower()
            ini_type = "string"

            # Resolve values passed from environment variables
            if not default or default in choices:
                pass
            elif "yes" in choices and default in _env.TRUE:
                default = "yes"
            elif "no" in choices and default in _env.FALSE:
                default = "no"
            else:
                raise ValueError(
                    f"Invalid value '{default}' for environment variable {self.environment}. "
                    f"Expecting one of {(*choices,)}"
                )
        else:
            default = _env.as_str(self.environment, default)
            ini_type = "string"

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
                f"Default: {self.default_in_help or default}"
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


def populate_ini_to_options(config: Config, options: Iterable[Option]) -> None:
    """Populate values from configuration files to command line options.

    Args:
        config: The pytest configuration object.
        options: List of options.
    """
    for option in options:
        value: Any = config.getoption(option.name)

        if value is None:
            setattr(config.option, option.name, config.getini(option.name))


def is_cocotb_option(name: str) -> bool:
    """Check if provided name is a cocotb option.

    Args:
        name: Name of option (command line argument, entry from configuration file, ...).

    Returns:
        True if option is cococtb option. Otherwise False.
    """
    return any(name.startswith(prefix) for prefix in PREFIXES)
