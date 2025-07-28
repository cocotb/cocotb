# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from typing import Any

import pytest

import cocotb
from cocotb.types import IndexingChangedWarning


@cocotb.test
async def test_indexing_warnings(dut: Any) -> None:
    with pytest.warns(IndexingChangedWarning, match="Update index 0 to 7"):
        dut.vec.value[0]
    with pytest.raises(IndexError):  # 3:7 is TO, but the HDL 7:0 is DOWNTO
        with pytest.warns(IndexingChangedWarning, match="Update slice 3:7 to 4:0"):
            dut.vec.value[3:7]

    with pytest.raises(IndexError):  # 0 is out of range of the HDL's 1:4
        with pytest.warns(IndexingChangedWarning, match="Update index 0 to 1"):
            dut.arr.value[0]
    with pytest.warns(IndexingChangedWarning, match="Update slice 1:2 to 2:3"):
        dut.arr.value[1:2]
