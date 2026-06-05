# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Specification of cocotb-specific hook functions for pytest."""

from __future__ import annotations

from pytest import FixtureRequest, hookspec

from cocotb_tools.pytest.dut import Dut


@hookspec(firstresult=True)
def pytest_cocotb_dut_create(request: FixtureRequest) -> Dut | None:
    """Create a new instance of :class:`cocotb_tools.pytest.dut.Dut`.

    This hook allows custom plugins or local configuration files to instantiate a custom
    subclass of :class:`~cocotb_tools.pytest.dut.Dut` with custom configuration defaults or behavior.

    .. note::

        Any ``conftest.py`` file can implement this hook. Execution stops at the first non-:data:`None` result.

    Example:

    .. code-block:: python

        from pytest import hookimpl, FixtureRequest
        from cocotb_tools.pytest.dut import Dut


        class MyDutExt(Dut):
            pass


        @hookimpl(tryfirst=True)
        def pytest_cocotb_dut_create(request: FixtureRequest) -> Dut | None:
            return MyDutExt(request)

    Args:
        request: The pytest fixture request.

    Returns:
        :data:`None` if pytest should invoke another implementation of this hook;
        otherwise, an instance of :class:`cocotb_tools.pytest.dut.Dut`.
    """


@hookspec(firstresult=True)
def pytest_cocotb_dut_run(dut: Dut) -> object:
    """Compile, elaborate, and run the HDL module with the simulator and cocotb tests.

    This hook allows custom runners or custom build/test orchestrators to be used
    instead of the default :class:`~cocotb_tools.runner.Runner`.

    .. note::

        Any ``conftest.py`` file can implement this hook. Execution stops at the first non-:data:`None` result.

    Example:

    .. code-block:: python

        from subprocess import run
        from pytest import hookimpl
        from cocotb_tools.pytest.dut import Dut


        @hookimpl(tryfirst=True)
        def pytest_cocotb_dut_run(dut: Dut) -> object:
            run(["make", dut.toplevel], check=True)
            return True

    Args:
        dut: An instance of :class:`~cocotb_tools.pytest.dut.Dut` containing the required configuration.

    Returns:
        :data:`None` if pytest should invoke another implementation of this hook;
        otherwise, any non-:data:`None` value to stop hook execution.
    """
