from __future__ import annotations

import inspect
from pathlib import Path
from shutil import which
from typing import Any

from pytest import FixtureRequest

from cocotb_tools.runner import (
    Runner,
    get_runner,
)

# Name of HDL simulator per executable
SIMULATORS: dict[str, str] = {
    # open-source simulators first
    "verilator": "verilator",
    "nvc": "nvc",
    "ghdl": "ghdl",
    "iverilog": "icarus",
    # proprietary simulators
    "xrun": "xcelium",
    "vcs": "vcs",
    "vsim": "questa",
    "vsimsa": "riviera",
}

BUILD_OPTIONS: tuple[str, ...] = tuple(inspect.signature(Runner.build).parameters)
TEST_OPTIONS: tuple[str, ...] = tuple(inspect.signature(Runner.test).parameters)


class HDL:
    def __init__(self, request: FixtureRequest, runner: Runner | None = None):
        super().__init__()

        simulator: str = request.config.option.cocotb_simulator

        self.request: FixtureRequest = request
        self.runner: Runner = runner or self._get_runner(simulator)

    @property
    def simulator(self) -> str:
        return str(self.runner.__class__.__name__).lower()

    def from_request(self, request: FixtureRequest) -> HDL:
        return HDL(request=request, runner=self.runner)

    def build(self, *args: Any, **kwargs: Any) -> None:
        options: dict[str, Any] = self._get_options(BUILD_OPTIONS)
        options.update(kwargs)
        self.runner.build(*args, **options)

    def test(self, *args: Any, **kwargs: Any) -> Path:
        assert self.request.scope == "function", (
            f"scope of pytest fixture request for '{self.request.node.name}' must be 'function'"
        )

        options: dict[str, Any] = self._get_options(TEST_OPTIONS)
        options.update(kwargs)

        return self.runner.test(*args, **options)

    @staticmethod
    def _get_runner(simulator: str) -> Runner:
        if not simulator or simulator == "auto":
            for command, name in SIMULATORS.items():
                if which(command):
                    simulator = name
                    break

        return get_runner(simulator)

    def _get_options(self, names: tuple[str, ...]) -> dict[str, Any]:
        request: FixtureRequest = self.request
        option = request.config.option
        node = request.node
        options: dict[str, Any] = {}

        for name in names:
            value: Any = getattr(option, f"cocotb_{name}", None)

            if value and value != "auto":
                options[name] = value

        for marker in reversed(list(node.iter_markers("cocotb"))):
            for name, value in marker.kwargs.items():
                if name in names:
                    options[name] = value

        return options
