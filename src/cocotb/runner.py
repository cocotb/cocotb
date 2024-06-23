# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import warnings

warnings.warn(
    "This module name is deprecated; use `cocotb_tools.runner` instead.",
    DeprecationWarning,
    stacklevel=2,
)

with warnings.catch_warnings():
    warnings.simplefilter(action="ignore", category=UserWarning)

    from cocotb_tools.runner import *  # noqa: E402, F403
