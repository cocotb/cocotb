# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import warnings
from typing import Any


def __getattr__(name: str) -> Any:
    if name == "TestSuccess":
        warnings.warn(
            "`raise TestSuccess` is deprecated. Use `cocotb.pass_test()` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from cocotb._test_functions import TestSuccess

        return TestSuccess

    elif name == "SimFailure":
        warnings.warn(
            "SimFailure was moved to `cocotb.regression`.",
            DeprecationWarning,
            stacklevel=2,
        )
        from cocotb.regression import SimFailure

        return SimFailure

    elif name == "SimTimeoutError":
        warnings.warn(
            "SimTimeoutError was moved from `cocotb.result` to `cocotb.triggers`.",
            DeprecationWarning,
            stacklevel=2,
        )
        from cocotb.triggers import SimTimeoutError

        return SimTimeoutError

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
