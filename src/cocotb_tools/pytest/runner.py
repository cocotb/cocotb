# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Module related with handling cocotb runners and collecting cocotb tests from these runners."""

from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from importlib import import_module
from pathlib import Path

from pytest import Collector, Item, Module


class Runner(Collector):
    """Collector that will collect cocotb tests from cocotb runner."""

    def __init__(
        self,
        item: Item,
        *args,
        **kwargs,
    ) -> None:
        """Create new instance of collector to collect cocotb tests
        from Python module(s) that will be run by cocotb runner.

        Args:
            item:        Cocotb runner test function.
            args:        Additional positional arguments for pytest collector.
            kwargs:      Additional named arguments for pytest collector.
        """
        super().__init__(*args, **kwargs)

        self.item: Item = item
        item.extra_keyword_matches.add("runner")

    def collect(self) -> Iterable[Item | Collector]:
        """Collect cocotb tests from Python module(s) that will be run by cocotb runner."""
        test_modules: str | Sequence[str] = []

        for marker in self.item.iter_markers("cocotb"):
            # test_module can be retrieved from positional arguments or named argument
            test_modules = marker.kwargs.get("test_module", marker.args)

            if test_modules:
                break

        if isinstance(test_modules, str):
            test_modules = [test_modules]

        if not test_modules:
            yield Module.from_parent(self, name=self.path.stem, path=self.path)

        for test_module in test_modules:
            path: Path = self.path.parent / Path(
                test_module.replace(".", os.path.pathsep) + ".py"
            )

            if not path.exists():
                path = Path(str(import_module(test_module).__file__))

            yield Module.from_parent(self, name=path.stem, path=path)
