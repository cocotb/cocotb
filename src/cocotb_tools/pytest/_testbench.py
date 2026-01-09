# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Module representing collection of cocotb tests."""

from __future__ import annotations

from pytest import Module


class Testbench(Module):
    """Collector that will collect cocotb tests from test modules."""
