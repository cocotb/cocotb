# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Module related with handling cocotb runners and collecting cocotb tests from these runners."""

from __future__ import annotations

import os
from collections.abc import Iterable
from importlib import import_module
from pathlib import Path
from typing import Any

from pytest import Collector, Item

from cocotb_tools.pytest.testbench import Testbench


class Runner(Collector):
    """Collector that will collect cocotb tests from cocotb runner."""

    def __init__(
        self,
        item: Item,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Create new instance of collector to collect cocotb tests
        from Python module(s) that will be run by cocotb runner.

        Args:
            item:   Cocotb runner test function.
            args:   Additional positional arguments for pytest collector.
            kwargs: Additional named arguments for pytest collector.
        """
        super().__init__(*args, **kwargs)

        self.item: Item = item

    def collect(self) -> Iterable[Item | Collector]:
        """Collect cocotb tests from Python module(s) that will be run by cocotb runner.

        Yields:
            Collected item or collector.
        """
        test_modules: Iterable[str] | None = None

        for marker in self.item.iter_markers("cocotb_runner"):
            if marker.args:
                test_modules = marker.args
                break

        for test_module in test_modules or (self.path.stem,):
            # Check if test_module exists as Python file
            path: Path = self.path.parent / Path(
                test_module.replace(".", os.path.pathsep) + ".py"
            )

            if not path.exists():
                # Try to get path to Python file by importing test_module as Python module
                path = Path(str(import_module(test_module).__file__))

            yield Testbench.from_parent(self, name=path.stem, path=path)
