# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import sys
from typing import TYPE_CHECKING, Dict, List, Union

from cocotb._decorators import (
    parametrize,
    test,
)
from cocotb._test import create_task, start, start_soon
from cocotb._test_functions import pass_test

from ._version import __version__ as _version

if TYPE_CHECKING:
    from logging import Logger
    from types import SimpleNamespace

    from cocotb._scheduler import Scheduler
    from cocotb.handle import SimHandleBase
    from cocotb.regression import RegressionManager

__all__ = (
    "RANDOM_SEED",
    "SIM_NAME",
    "SIM_VERSION",
    "__version__",
    "argv",
    "create_task",
    "is_simulation",
    "log",
    "packages",
    "parametrize",
    "pass_test",
    "plusargs",
    "start",
    "start_soon",
    "test",
    "top",
)

# Set __module__ on re-exports
test.__module__ = __name__
start_soon.__module__ = __name__
start.__module__ = __name__
create_task.__module__ = __name__
parametrize.__module__ = __name__
pass_test.__module__ = __name__


__version__: str = _version
"""The version of cocotb."""


log: "Logger"
"""An easily accessible :class:`~logging.Logger` for the user.

This logger defaults to the :data:`logging.INFO` log level.

.. versionchanged:: 2.0
    This was previously the ``"cocotb"`` Logger.
    It is now a Logger under the ``"test"`` namespace.
"""

_scheduler_inst: "Scheduler"
"""The global scheduler instance."""

_regression_manager: "RegressionManager"
"""The global regression manager instance."""

argv: List[str]
"""The argument list as seen by the simulator."""

plusargs: Dict[str, Union[bool, str]]
"""A dictionary of "plusargs" handed to the simulation.

See :envvar:`COCOTB_PLUSARGS` for details.
"""

packages: "SimpleNamespace"
"""A :class:`python:types.SimpleNamespace` of package handles.

This will be populated with handles at test time if packages can be discovered
via the GPI.

.. versionadded:: 2.0
"""

SIM_NAME: str
"""The product information of the running simulator."""

SIM_VERSION: str
"""The version of the running simulator."""

RANDOM_SEED: int
"""The last value used to seed the global PRNG.

During test collection, this is set to the value provided by :envvar:`COCOTB_RANDOM_SEED`,
if given, or a random value based on the state of the operating system.

During test run, this is set to a new value computed by combining the value used during test collection,
with the full test name (e.g. ``my_test_module.my_test``).
"""

top: "SimHandleBase"
r"""
A handle to the :envvar:`COCOTB_TOPLEVEL` entity/module.

This is equivalent to the :term:`DUT` parameter given to cocotb tests, so it can be used wherever that variable can be used.
It is particularly useful for extracting information about the :term:`DUT` in module-level class and function definitions;
and in parameters to :class:`.TestFactory`\ s.
"""

is_simulation: bool = False
"""``True`` if cocotb was loaded in a simulation."""


if sys.version_info < (3, 9):
    import warnings

    warnings.warn(
        "Support for Python versions < 3.9 will be dropped in version 2.1",
        FutureWarning,
    )
