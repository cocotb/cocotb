# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Deprecated alias of :mod:`cocotb_previews`.

.. deprecated:: 2.2
    Use :mod:`cocotb_previews` instead.
"""

from __future__ import annotations

import sys
import types
import warnings

import cocotb_previews


class _DeprecatedModule(types.ModuleType):
    def __getattr__(self, name: str) -> object:
        if (name.startswith("__") and name.endswith("__")) or not hasattr(
            cocotb_previews, name
        ):
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        warnings.warn(
            "`cocotb.preview` has been moved to `cocotb_previews`.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(cocotb_previews, name)

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("__") and name.endswith("__"):
            super().__setattr__(name, value)
            return
        warnings.warn(
            "`cocotb.preview` has been moved to `cocotb_previews`.",
            DeprecationWarning,
            stacklevel=2,
        )
        setattr(cocotb_previews, name, value)


# Module-level __setattr__ is not supported by the language, so this hacky approach is required.
sys.modules[__name__].__class__ = _DeprecatedModule
