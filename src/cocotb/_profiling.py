# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause


# Debug mode controlled by environment variables
import cProfile
import os
import pstats
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING

from cocotb._py_compat import nullcontext

if TYPE_CHECKING:
    profiling_context: AbstractContextManager[None, None]


if "COCOTB_ENABLE_PROFILING" in os.environ:
    _profile: cProfile.Profile

    def initialize() -> None:
        global _profile
        _profile = cProfile.Profile()

    def finalize() -> None:
        ps = pstats.Stats(_profile).sort_stats("cumulative")
        ps.dump_stats("cocotb.pstat")

    if TYPE_CHECKING:

        class _ProfilingContextBase(AbstractContextManager[None, None]): ...
    else:

        class _ProfilingContextBase(AbstractContextManager): ...

    class _profiling_context(_ProfilingContextBase):
        """Context manager that profiles its contents"""

        def __enter__(self) -> None:
            _profile.enable()

        def __exit__(self, *excinfo: object) -> None:
            _profile.disable()

    profiling_context = _profiling_context()

else:

    def initialize() -> None:
        pass

    def finalize() -> None:
        pass

    profiling_context = nullcontext()
