# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import warnings


def __getattr__(name: str) -> object:
    if name == "TestSuccess":
        warnings.warn(
            "`raise TestSuccess` is deprecated. Use `cocotb.pass_test()` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from cocotb._test_functions import TestSuccess  # noqa: PLC0415

        return TestSuccess

    elif name == "SimFailure":
        warnings.warn(
            "SimFailure was moved to `cocotb.regression`.",
            DeprecationWarning,
            stacklevel=2,
        )
        from cocotb.regression import SimFailure  # noqa: PLC0415

        return SimFailure

    elif name == "SimTimeoutError":
        warnings.warn(
            "SimTimeoutError was moved from `cocotb.result` to `cocotb.triggers`.",
            DeprecationWarning,
            stacklevel=2,
        )
        from cocotb.triggers import SimTimeoutError  # noqa: PLC0415

        return SimTimeoutError

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
