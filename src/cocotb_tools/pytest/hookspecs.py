# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Specification of cocotb hook functions."""

from __future__ import annotations

from pytest import FixtureRequest, hookspec

from cocotb_tools.pytest.hdl import HDL
from cocotb_tools.runner import Runner


@hookspec(firstresult=True)
def pytest_cocotb_make_hdl(request: FixtureRequest) -> HDL | None:
    """Create new instance of :py:class:`cocotb_tools.pytest.hdl.HDL`.

    .. note::

        Any conftest file can implement this hook. Stops at first non-None result.

    Args:
        request: The pytest fixture request object.

    Returns:
        New instance of HDL.
    """


@hookspec(firstresult=True)
def pytest_cocotb_make_runner(simulator_name: str) -> Runner | None:
    """Create new instance of :py:class:`cocotb_tools.runner.Runner`.

    .. note::

        Any conftest file can implement this hook. Stops at first non-None result.

    Args:
        simulator_name: Name of HDL simulator.

    Returns:
        New instance of runner.
    """
