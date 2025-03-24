# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import logging as py_logging
from types import SimpleNamespace
from typing import Dict, List, Union

import cocotb._profiling
import cocotb.handle
import cocotb.task
import cocotb.triggers
from cocotb._decorators import (
    bridge,
    parametrize,
    resume,
    test,
)
from cocotb._scheduler import Scheduler
from cocotb._test import create_task, pass_test, start, start_soon
from cocotb.regression import RegressionManager

from ._version import __version__

__all__ = (
    "bridge",
    "resume",
    "test",
    "parametrize",
    "pass_test",
    "create_task",
    "start",
    "start_soon",
    "__version__",
)


log: py_logging.Logger
"""An easily accessible :class:`~logging.Logger` for the user.

This logger defaults to the :data:`logging.INFO` log level.

.. versionchanged:: 2.0
    This was previously the ``"cocotb"`` Logger.
    It is now a Logger under the ``"test"`` namespace.
"""

_scheduler_inst: Scheduler
"""The global scheduler instance."""

regression_manager: RegressionManager
"""The global regression manager instance."""

argv: List[str]
"""The argument list as seen by the simulator."""

plusargs: Dict[str, Union[bool, str]]
"""A dictionary of "plusargs" handed to the simulation.

See :make:var:`COCOTB_PLUSARGS` for details.
"""

packages: SimpleNamespace
"""A :class:`python:types.SimpleNamespace` of package handles.

This will be populated with handles at test time if packages can be discovered
via the GPI.

.. versionadded:: 2.0
"""

SIM_NAME: str
"""The product information of the running simulator."""

SIM_VERSION: str
"""The version of the running simulator."""

_random_seed: int
"""
The value passed to the Python default random number generator.

See :envvar:`COCOTB_RANDOM_SEED` for details on how the value is computed.
This is guaranteed to hold a value at test time.
"""

top: cocotb.handle.SimHandleBase
r"""
A handle to the :envvar:`COCOTB_TOPLEVEL` entity/module.

This is equivalent to the :term:`DUT` parameter given to cocotb tests, so it can be used wherever that variable can be used.
It is particularly useful for extracting information about the :term:`DUT` in module-level class and function definitions;
and in parameters to :class:`.TestFactory`\ s.
"""

is_simulation: bool = False
"""``True`` if cocotb was loaded in a simulation."""
