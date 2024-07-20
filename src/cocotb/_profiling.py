# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause


# Debug mode controlled by environment variables
import cProfile
import os
import pstats
from typing import Union

from cocotb._py_compat import nullcontext

_profile: Union[cProfile.Profile, None]


class _profiling_context:
    """Context manager that profiles its contents"""

    def __enter__(self):
        _profile.enable()

    def __exit__(self, *excinfo):
        _profile.disable()


if "COCOTB_ENABLE_PROFILING" in os.environ:
    _profile = cProfile.Profile()

    def finalize() -> None:
        ps = pstats.Stats(_profile).sort_stats("cumulative")
        ps.dump_stats("cocotb.pstat")

    profiling_context = _profiling_context()

else:
    _profile = None

    def finalize() -> None:
        pass

    profiling_context = nullcontext()
