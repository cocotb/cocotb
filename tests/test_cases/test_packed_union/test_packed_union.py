# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os

import pytest

import cocotb
from cocotb.handle import PackedArrayObject, PackedUnionObject
from cocotb_tools.sim_versions import RivieraVersion, VerilatorVersion

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()

# Icarus Verilog and Verilator before 5.053 flatten packed unions into vectors.
FLATTENS_PACKED_UNION = SIM_NAME.startswith("icarus") or (
    SIM_NAME.startswith("verilator")
    and VerilatorVersion(cocotb.SIM_VERSION) < VerilatorVersion("5.053")
)

# Riviera-PRO 2022.10-2023.10 (VPI) do not discover dut.t correctly (gh-3587)
DISCOVERY_BROKEN = SIM_NAME.startswith("ghdl") or (
    SIM_NAME.startswith("riviera")
    and RivieraVersion(cocotb.SIM_VERSION) >= RivieraVersion("2022.10")
    and RivieraVersion(cocotb.SIM_VERSION) < RivieraVersion("2024.04")
    and LANGUAGE == "verilog"
)


@cocotb.test(
    expect_error=Exception
    if FLATTENS_PACKED_UNION or DISCOVERY_BROKEN
    else (AttributeError)
)
async def test_packed_union(dut):
    pbs = dut.t
    pbs.a.value = 0


@cocotb.test(expect_error=Exception if DISCOVERY_BROKEN else ())
async def test_packed_union_type(dut):
    """A packed union is a PackedUnionObject where the simulator reports it"""

    if FLATTENS_PACKED_UNION:
        assert type(dut.t) is PackedArrayObject
        assert dut.t._type == "GPI_PACKED_ARRAY"
    else:
        assert type(dut.t) is PackedUnionObject
        assert dut.t._type == "GPI_PACKED_UNION"
        with pytest.raises(TypeError):
            _ = dut.t.range
        with pytest.raises(TypeError):
            dut.t[0]
    assert dut.t.size == 4
