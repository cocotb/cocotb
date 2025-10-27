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
    """Collector that will collect cocotb tests from cocotb runner based on
    provided ``test_module`` argument."""

    def __init__(
        self,
        item: Item,
        test_module: Sequence[str] | str = "",
        *args,
        **kwargs,
    ):
        """Create new instance of collector to collect cocotb tests
        from Python module(s) that will be run by cocotb runner.

        Args:
            item:        Cocotb runner test function.
            test_module: Name of Python module with cocotb tests.
            args:        Additional positional arguments for pytest collector.
            kwargs:      Additional named arguments for pytest collector.
        """
        super().__init__(*args, **kwargs)

        if isinstance(test_module, str):
            test_module = [test_module] if test_module else []

        self.item: Item = item
        self.test_modules: Sequence[str] = test_module
        item.extra_keyword_matches.add("runner")

    def collect(self) -> Iterable[Item | Collector]:
        """Collect cocotb tests from Python module(s) that will be run by cocotb runner."""
        for test_module in self.test_modules:
            path: Path = self.path.parent / Path(
                test_module.replace(".", os.path.pathsep) + ".py"
            )

            if not path.exists():
                path = Path(str(import_module(test_module).__file__))

            yield Module.from_parent(self, name=path.stem, path=path)
