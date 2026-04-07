# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause


# Debug mode controlled by environment variables
from __future__ import annotations

import cProfile
import pstats
from contextlib import AbstractContextManager, nullcontext

import cocotb._shutdown
from cocotb_tools import _env

profiling_context: AbstractContextManager[None, None]


if _env.as_bool("COCOTB_ENABLE_PROFILING"):
    _profile: cProfile.Profile

    def _init() -> None:
        global _profile
        _profile = cProfile.Profile()

        def finalize() -> None:
            ps = pstats.Stats(_profile).sort_stats("cumulative")
            ps.dump_stats("cocotb.pstat")

        cocotb._shutdown.register(finalize)

    class _profiling_context(AbstractContextManager[None, None]):
        """Context manager that profiles its contents."""

        def __enter__(self) -> None:
            _profile.enable()

        def __exit__(self, *excinfo: object) -> None:
            _profile.disable()

    profiling_context = _profiling_context()

else:

    def _init() -> None:
        pass

    profiling_context = nullcontext()
