# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Specification of cocotb hook functions."""

from __future__ import annotations

from pytest import FixtureRequest, hookspec

from cocotb_tools.pytest.hdl import HDL


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
def pytest_cocotb_hdl_build(hdl: HDL) -> object | None:
    """Build a HDL design.

    .. note::

        Any conftest file can implement this hook. Stops at first non-None result.

    Args:
        hdl: Instance of HDL design to build.
    """


@hookspec(firstresult=True)
def pytest_cocotb_hdl_test(hdl: HDL) -> object | None:
    """Test a HDL design.

    .. note::

        Any conftest file can implement this hook. Stops at first non-None result.

    Args:
        hdl: Instance of HDL design to test.
    """
