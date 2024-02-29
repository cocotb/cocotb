# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import warnings

warnings.warn(
    "This module name is deprecated; use `cocotb_tools.config` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from cocotb_tools.config import *  # noqa: E402, F403
