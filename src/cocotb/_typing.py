# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from cocotb._py_compat import Literal, TypeAlias

TimeUnit: TypeAlias = Literal["step", "fs", "ps", "ns", "us", "ms", "sec"]
