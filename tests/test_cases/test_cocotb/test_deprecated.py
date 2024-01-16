# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import cocotb
import pytest


# identifiers starting with `_` are illegal in VHDL
@cocotb.test(skip=cocotb.LANGUAGE in ("vhdl"))
async def test_id_deprecated(dut):
    with pytest.warns(DeprecationWarning):
        dut._id("_underscore_name", extended=False)
