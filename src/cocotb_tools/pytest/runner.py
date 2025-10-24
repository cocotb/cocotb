# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Module related with handling cocotb runners and collecting cocotb tests from these runners."""

from __future__ import annotations

import os
from collections.abc import Iterable
from importlib import import_module
from pathlib import Path

from pytest import Collector, Item, Module


class Runner(Collector):
    """Collector that will collect cocotb tests from cocotb runners based on
    modules names defined in ``x``."""

    def __init__(
        self,
        item: Item,
        modules: Iterable[str] | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.item: Item = item
        self.modules: list[str] = list(modules) if modules else []
        item.extra_keyword_matches.add("runner")

    def collect(self) -> Iterable[Item | Collector]:
        if not self.modules:
            yield Module.from_parent(self, name=self.path.stem, path=self.path)

        for module in self.modules:
            path: Path = self.path.parent / Path(
                module.replace(".", os.path.pathsep) + ".py"
            )

            if not path.exists():
                path = Path(str(import_module(module).__file__))

            yield Module.from_parent(self, name=path.stem, path=path)
