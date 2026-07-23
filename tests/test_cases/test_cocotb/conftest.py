# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import pytest

import cocotb


@pytest.fixture(name="_")
def underscore_fixture():
    """To make pytest happy about cocotb tests that are using the underscore ``_`` as first argument."""
    return cocotb.top
