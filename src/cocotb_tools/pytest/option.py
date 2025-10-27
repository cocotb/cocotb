# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Generic option used as command line argument and entry in configuration file."""

from __future__ import annotations

import shlex
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pytest import OptionGroup, Parser

from cocotb_tools.pytest import env

PREFIXES: tuple[str, ...] = ("cocotb_", "gpi_", "pygpi_")


class Option:
    """Representation of single cocotb option that can be set from
    configuration file, environment variable or command line."""

    def __init__(
        self,
        name: str,
        default: Any = None,
        default_in_help: str | None = None,
        environment: str | None = None,
        **kwargs,
    ):
        self.name: str = name
        self.extra: dict[str, Any] = dict(kwargs)
        self.default: Any = default
        self.default_in_help: str | None = default_in_help
        self.environment: str = environment if environment else name.upper()

    def get(self, key: str, default: Any = None) -> None:
        return self.extra.get(key, default)

    def __setitem__(self, key: str, value: Any) -> None:
        self.extra[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.extra[key]

    def __contains__(self, item: str) -> bool:
        return item in self.extra

    def add_to_parser(self, parser: Parser, group: OptionGroup) -> None:
        argument: str = "--" + self.name.replace("_", "-")
        default: Any = self.default
        action: str | None = self.get("action")
        nargs: str | None = self.get("nargs")
        extra: dict[str, Any] = {}
        kind: str = ""

        if action == "store_true":
            default = env.as_bool(self.environment, default)
            kind = "bool"
        elif nargs:
            default = env.as_list(self.environment, default)
            extra["metavar"] = "NAME"
            kind = "args"
        elif isinstance(default, int):
            default = env.as_int(self.environment, default)
            extra = {"type": int, "metavar": "INTEGER"}
            kind = "int"
        elif isinstance(default, Path):
            default = env.as_path(self.environment, default)
            extra = {"type": Path, "metavar": "PATH"}
            kind = "paths"
        elif isinstance(default, list):
            default = shlex.split(env.as_str(self.environment, default))
            extra = {"type": shlex.split, "metavar": "ARGUMENTS"}
            kind = "args"
        else:
            default = env.as_str(self.environment, default)
            extra["type"] = str
            kind = "string"

            if "choices" not in self.extra:
                if default == "1":
                    default = "yes"
                elif default == "0":
                    default = "no"

                extra["metavar"] = "NAME"

        default_in_help: Any = self.default_in_help if self.default_in_help else default

        extra.update(self.extra)
        extra["help"] += (
            f"\nEnvironment variable: {self.environment}\nDefault: {default_in_help}"
        )
        parser.addini(
            self.name, help=f"Default value for {argument}", type=kind, default=default
        )
        group.addoption(argument, **extra)


def add_options_to_parser(parser: Parser, name: str, options: Iterable[Option]) -> None:
    group: OptionGroup = parser.getgroup(name, description=f"{name} options")

    for option in options:
        option.add_to_parser(parser, group)


def is_cocotb_option(name: str) -> bool:
    """Check if provided name is a cocotb option.

    Args:
        name: Name of option (command line argument, entry from configuration file, ...).

    Returns:
        ``True`` if option is cococtb option. Otherwise ``False``.
    """
    return any(name.startswith(prefix) for prefix in PREFIXES)
